import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem

from core.config import settings
from core.storage import download_file, upload_file
from models.schemas import DockingInput
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

MAX_SMILES = 10000


class DockingModule(BaseModule):
    """Wraps AutoDock Vina for molecular docking."""

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, DockingInput):
            return False, "Input must be DockingInput"
        if not input.pdb_path:
            return False, "pdb_path is required"
        if not input.smiles_list:
            return False, "smiles_list must not be empty"
        if len(input.smiles_list) > MAX_SMILES:
            return False, f"Maximum {MAX_SMILES} SMILES allowed"
        if input.exhaustiveness < 1 or input.exhaustiveness > 64:
            return False, "exhaustiveness must be between 1 and 64"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, DockingInput)

        workdir = Path(tempfile.mkdtemp(prefix=f"docking_{input.job_id}_"))
        try:
            return self._run_docking(input, workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _run_docking(self, input: DockingInput, workdir: Path) -> ModuleOutput:
        warnings: list[str] = []

        # Download receptor PDB from MinIO
        receptor_pdb = workdir / "receptor.pdb"
        try:
            bucket, key = input.pdb_path.split("/", 1)
            pdb_data = download_file(bucket, key)
            receptor_pdb.write_bytes(pdb_data)
        except Exception as e:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=[f"Could not download receptor PDB: {e}"],
            )

        # Step A: Pocket detection (if no binding site provided)
        binding_site = input.binding_site
        pocket_auto = False
        if binding_site is None:
            binding_site = self._detect_pocket(receptor_pdb)
            if binding_site is None:
                return ModuleOutput(
                    job_id=input.job_id, status="failed", data={},
                    errors=["No druggable pocket detected. Provide binding_site manually."],
                )
            pocket_auto = True

        # Step B: Prepare receptor PDBQT
        receptor_pdbqt = workdir / "receptor.pdbqt"
        try:
            subprocess.run(
                ["obabel", str(receptor_pdb), "-O", str(receptor_pdbqt), "-xr"],
                check=True, capture_output=True, timeout=60,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=[f"Receptor preparation failed: {e}"],
            )

        # Step C: Dock each ligand
        results = []
        failed_smiles = []

        def dock_one(idx: int, smiles: str) -> dict | None:
            return self._dock_single_ligand(
                smiles, idx, receptor_pdbqt, binding_site,
                input.exhaustiveness, input.num_poses, workdir,
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(dock_one, i, smi): smi
                for i, smi in enumerate(input.smiles_list)
            }
            for future in as_completed(futures):
                smi = futures[future]
                try:
                    result = future.result()
                    if result is None:
                        failed_smiles.append(smi)
                    else:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Docking failed for {smi}: {e}")
                    failed_smiles.append(smi)

        if not results and failed_smiles:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=[f"All {len(failed_smiles)} ligands failed docking"],
            )

        # Step D: Sort by best affinity and assign ranks
        results.sort(key=lambda r: r["best_affinity_kcal_mol"])
        # Filter out trivial non-binders
        results = [r for r in results if r["best_affinity_kcal_mol"] < -4.0]

        for rank, r in enumerate(results, 1):
            r["rank"] = rank

        # Upload pose files to MinIO
        for r in results:
            local_path = r.pop("_local_pose_path", None)
            if local_path and Path(local_path).exists():
                try:
                    pose_key = f"{input.job_id}/pose_{r['rank']}.pdbqt"
                    upload_file("results", pose_key, Path(local_path).read_bytes())
                    r["pose_pdbqt_path"] = f"results/{pose_key}"
                except Exception:
                    r["pose_pdbqt_path"] = None

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data={
                "docked_count": len(results),
                "failed_count": len(failed_smiles),
                "failed_smiles": failed_smiles,
                "binding_site_used": binding_site,
                "pocket_detected_automatically": pocket_auto,
                "results": results,
            },
            warnings=warnings,
        )

    def _detect_pocket(self, receptor_pdb: Path) -> dict | None:
        """Run fpocket and extract the top druggable pocket centroid."""
        try:
            subprocess.run(
                ["fpocket", "-f", str(receptor_pdb)],
                check=True, capture_output=True, timeout=120,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        out_dir = receptor_pdb.parent / f"{receptor_pdb.stem}_out"
        info_file = out_dir / f"{receptor_pdb.stem}_info.txt"
        pockets_dir = out_dir / "pockets"

        if not info_file.exists():
            return None

        # Parse info file to find best druggable pocket
        best_pocket_idx = self._find_best_pocket(info_file)
        if best_pocket_idx is None:
            return None

        # Extract centroid from the pocket PDB file
        pocket_pdb = pockets_dir / f"pocket{best_pocket_idx}_atm.pdb"
        if not pocket_pdb.exists():
            return None

        return self._compute_pocket_centroid(pocket_pdb)

    def _find_best_pocket(self, info_file: Path) -> int | None:
        """Find the pocket index with the highest druggability score."""
        text = info_file.read_text()
        best_idx = None
        best_score = 0.0
        current_idx = 0

        for block in re.split(r"Pocket\s+(\d+)\s*:", text):
            # Try to parse as pocket index
            try:
                current_idx = int(block.strip())
                continue
            except ValueError:
                pass

            druggability = 0.0
            volume = 0.0
            for line in block.splitlines():
                line = line.strip()
                if "Druggability Score" in line:
                    match = re.search(r"[\d.]+", line.split(":")[-1])
                    if match:
                        druggability = float(match.group())
                elif line.startswith("Volume") and "score" not in line.lower():
                    match = re.search(r"[\d.]+", line.split(":")[-1])
                    if match:
                        volume = float(match.group())

            if druggability > best_score and volume > 100:
                best_score = druggability
                best_idx = current_idx

        return best_idx if best_score > 0.3 else None

    def _compute_pocket_centroid(self, pocket_pdb: Path) -> dict:
        """Compute the centroid of ATOM records in a pocket PDB file."""
        xs, ys, zs = [], [], []
        for line in pocket_pdb.read_text().splitlines():
            if line.startswith("ATOM") or line.startswith("HETATM"):
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                except (ValueError, IndexError):
                    continue

        if not xs:
            return {"center_x": 0, "center_y": 0, "center_z": 0,
                    "size_x": 20.0, "size_y": 20.0, "size_z": 20.0}

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        cz = sum(zs) / len(zs)

        # Size = range + 10 Å padding, minimum 20 Å
        sx = max(20.0, (max(xs) - min(xs)) + 10.0)
        sy = max(20.0, (max(ys) - min(ys)) + 10.0)
        sz = max(20.0, (max(zs) - min(zs)) + 10.0)

        return {
            "center_x": round(cx, 2),
            "center_y": round(cy, 2),
            "center_z": round(cz, 2),
            "size_x": round(sx, 2),
            "size_y": round(sy, 2),
            "size_z": round(sz, 2),
        }

    def _dock_single_ligand(
        self, smiles: str, idx: int, receptor_pdbqt: Path,
        binding_site: dict, exhaustiveness: int, num_poses: int,
        workdir: Path,
    ) -> dict | None:
        """Dock a single SMILES against the receptor. Returns result dict or None on failure."""

        # Validate SMILES with RDKit
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        ligand_dir = workdir / f"ligand_{idx}"
        ligand_dir.mkdir(exist_ok=True)

        # Generate 3D conformer
        try:
            mol = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            if AllChem.EmbedMolecule(mol, params) == -1:
                return None
            AllChem.MMFFOptimizeMolecule(mol)
        except Exception:
            return None

        # Write SDF
        sdf_path = ligand_dir / "ligand.sdf"
        writer = Chem.SDWriter(str(sdf_path))
        writer.write(mol)
        writer.close()

        # Convert to PDBQT
        pdbqt_path = ligand_dir / "ligand.pdbqt"
        try:
            subprocess.run(
                ["obabel", str(sdf_path), "-O", str(pdbqt_path)],
                check=True, capture_output=True, timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        # Run Vina
        output_path = ligand_dir / "poses.pdbqt"
        cmd = [
            "vina",
            "--receptor", str(receptor_pdbqt),
            "--ligand", str(pdbqt_path),
            "--center_x", str(binding_site["center_x"]),
            "--center_y", str(binding_site["center_y"]),
            "--center_z", str(binding_site["center_z"]),
            "--size_x", str(binding_site.get("size_x", 20)),
            "--size_y", str(binding_site.get("size_y", 20)),
            "--size_z", str(binding_site.get("size_z", 20)),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_poses),
            "--out", str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        # Parse affinities from stdout (Vina 1.2.5 outputs results to stdout)
        affinities = self._parse_vina_output(result.stdout)
        if not affinities:
            return None

        return {
            "smiles": smiles,
            "rank": 0,  # assigned later
            "best_affinity_kcal_mol": affinities[0],
            "all_pose_affinities": affinities,
            "pose_pdbqt_path": None,
            "docking_success": True,
            "_local_pose_path": str(output_path),
        }

    def _parse_vina_output(self, text: str) -> list[float]:
        """Parse AutoDock Vina stdout for binding affinities."""
        affinities = []
        in_results = False
        for line in text.splitlines():
            if "-----+------------" in line:
                in_results = True
                continue
            if in_results:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        affinities.append(float(parts[1]))
                    except ValueError:
                        break
                else:
                    break
        return affinities

    def _parse_vina_log(self, log_path: Path) -> list[float]:
        """Parse AutoDock Vina log file for binding affinities (legacy)."""
        if not log_path.exists():
            return []
        return self._parse_vina_output(log_path.read_text())

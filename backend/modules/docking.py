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
        """Run fpocket and parse the top druggable pocket."""
        try:
            subprocess.run(
                ["fpocket", "-f", str(receptor_pdb)],
                check=True, capture_output=True, timeout=120,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        # fpocket creates a directory like receptor_out/
        out_dir = receptor_pdb.parent / f"{receptor_pdb.stem}_out"
        info_file = out_dir / f"{receptor_pdb.stem}_info.txt"

        if not info_file.exists():
            # Try alternate path
            pockets_dir = out_dir / "pockets"
            if not pockets_dir.exists():
                return None
            info_file = out_dir / f"{receptor_pdb.stem}_info.txt"
            if not info_file.exists():
                return None

        return self._parse_fpocket_output(info_file)

    def _parse_fpocket_output(self, info_file: Path) -> dict | None:
        """Parse fpocket info file for the best druggable pocket."""
        text = info_file.read_text()
        pockets = []

        # Parse pocket blocks
        for block in re.split(r"Pocket\s+\d+\s*:", text):
            center = {}
            druggability = 0.0
            volume = 0.0

            for line in block.splitlines():
                line = line.strip()
                if "Score" in line and "Druggability" in line:
                    match = re.search(r"[\d.]+", line.split(":")[-1])
                    if match:
                        druggability = float(match.group())
                elif "Volume" in line:
                    match = re.search(r"[\d.]+", line.split(":")[-1])
                    if match:
                        volume = float(match.group())
                elif "Center" in line:
                    nums = re.findall(r"-?[\d.]+", line)
                    if len(nums) >= 3:
                        center = {
                            "center_x": float(nums[0]),
                            "center_y": float(nums[1]),
                            "center_z": float(nums[2]),
                        }

            if center and druggability > 0.5 and volume > 200:
                pockets.append({
                    **center,
                    "size_x": 20.0, "size_y": 20.0, "size_z": 20.0,
                    "_druggability": druggability,
                })

        if not pockets:
            return None

        best = max(pockets, key=lambda p: p.pop("_druggability"))
        return best

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
        log_path = ligand_dir / "vina.log"
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
            "--log", str(log_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return None

        # Parse Vina log for affinities
        affinities = self._parse_vina_log(log_path)
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

    def _parse_vina_log(self, log_path: Path) -> list[float]:
        """Parse AutoDock Vina log file for binding affinities."""
        if not log_path.exists():
            return []

        affinities = []
        in_results = False
        for line in log_path.read_text().splitlines():
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

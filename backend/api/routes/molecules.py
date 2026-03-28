import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session

router = APIRouter()


@router.get("/render")
async def render_molecule(
    smiles: str = Query(..., description="SMILES string to render"),
    size: int = Query(default=200, ge=50, le=600),
) -> Response:
    """Render a 2D structure image from a SMILES string."""
    from rdkit import Chem
    from rdkit.Chem import Draw

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        img = Draw.MolToImage(Chem.MolFromSmiles("C"), size=(size, size))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    img = Draw.MolToImage(mol, size=(size, size))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


class ExportSdfRequest(BaseModel):
    job_id: str
    smiles_list: list[str] | None = None
    indices: list[int] | None = None


@router.post("/export-sdf")
async def export_sdf(
    request: ExportSdfRequest,
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Export molecules as an SDF file with 3D conformers."""
    smiles_list = request.smiles_list or []

    # If job_id provided and no smiles_list, try loading from job results
    if not smiles_list and request.job_id:
        from models.database import Job
        import uuid as uuid_mod
        try:
            uid = uuid_mod.UUID(request.job_id)
            result = await db.execute(select(Job).where(Job.id == uid))
            job = result.scalar_one_or_none()
            if job and job.output_data:
                candidates = job.output_data.get("ranked_candidates", [])
                if request.indices:
                    candidates = [c for c in candidates if c.get("rank") in request.indices]
                smiles_list = [c["smiles"] for c in candidates if "smiles" in c]
        except Exception:
            pass

    if not smiles_list:
        raise HTTPException(status_code=422, detail="No molecules to export")

    from rdkit import Chem
    from rdkit.Chem import AllChem

    sdf_io = io.StringIO()
    w = Chem.SDWriter(sdf_io)

    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        if AllChem.EmbedMolecule(mol, params) != -1:
            AllChem.MMFFOptimizeMolecule(mol)
        mol.SetProp("SMILES", smi)
        w.write(mol)

    w.close()
    sdf_content = sdf_io.getvalue()

    return Response(
        content=sdf_content.encode(),
        media_type="chemical/x-mdl-sdfile",
        headers={
            "Content-Disposition": f"attachment; filename=molecules_{request.job_id[:8]}.sdf",
        },
    )


class ValidateRequest(BaseModel):
    smiles_list: list[str]


@router.post("/validate")
async def validate_smiles(request: ValidateRequest) -> list[dict]:
    """Validate a list of SMILES strings."""
    from rdkit import Chem

    results = []
    for smi in request.smiles_list:
        smi = smi.strip()
        if not smi:
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            results.append({"smiles": smi, "valid": True, "error": None})
        else:
            results.append({"smiles": smi, "valid": False, "error": "Invalid SMILES"})
    return results


@router.post("/generate")
async def generate_molecules(
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Dispatch de novo molecule generation job — placeholder."""
    job_id = str(uuid.uuid4())
    return {"job_id": job_id, "status": "pending"}

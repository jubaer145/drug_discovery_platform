import logging

from rdkit import Chem
from rdkit.Chem import Descriptors, QED, AllChem
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

from models.schemas import AdmetInput, AdmetTier1, AdmetProfile
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

# Build PAINS filter catalog once
_pains_params = FilterCatalogParams()
_pains_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
_pains_catalog = FilterCatalog(_pains_params)

MAX_SMILES = 10000


class AdmetModule(BaseModule):
    """Predicts ADMET properties using RDKit descriptors (Tier 1)."""

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, AdmetInput):
            return False, "Input must be AdmetInput"
        if not input.smiles_list:
            return False, "smiles_list must not be empty"
        if len(input.smiles_list) > MAX_SMILES:
            return False, f"Maximum {MAX_SMILES} SMILES allowed"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, AdmetInput)

        profiles: list[dict] = []
        warnings: list[str] = []

        for smiles in input.smiles_list:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                warnings.append(f"Invalid SMILES skipped: {smiles}")
                continue

            tier1 = _compute_tier1(mol)
            overall, recommendation = _traffic_light(tier1)
            flags = _generate_flags(tier1, overall)

            profile = AdmetProfile(
                smiles=smiles,
                overall=overall,
                recommendation=recommendation,
                tier1=tier1,
                tier2=None,
                flags=flags,
            )
            profiles.append(profile.model_dump())

        if not profiles:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=["No valid SMILES provided"],
            )

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data={
                "profiles": profiles,
                "total": len(profiles),
                "skipped": len(input.smiles_list) - len(profiles),
                "green_count": sum(1 for p in profiles if p["overall"] == "GREEN"),
                "amber_count": sum(1 for p in profiles if p["overall"] == "AMBER"),
                "red_count": sum(1 for p in profiles if p["overall"] == "RED"),
            },
            warnings=warnings,
        )


def _compute_tier1(mol: Chem.Mol) -> AdmetTier1:
    """Compute RDKit Tier 1 ADMET descriptors."""
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    tpsa = Descriptors.TPSA(mol)
    rot_bonds = Descriptors.NumRotatableBonds(mol)
    qed_score = QED.qed(mol)

    # Lipinski violations
    violations = []
    if mw >= 500:
        violations.append("MW >= 500")
    if logp >= 5:
        violations.append("LogP >= 5")
    if hbd >= 5:
        violations.append("HBD >= 5")
    if hba >= 10:
        violations.append("HBA >= 10")
    lipinski_pass = len(violations) == 0

    # PAINS filter
    has_pains = _pains_catalog.HasMatch(mol)

    # SA score (simplified — use RDKit's built-in if available)
    sa_score = _calculate_sa_score(mol)

    return AdmetTier1(
        mw=round(mw, 2),
        logp=round(logp, 2),
        hbd=hbd,
        hba=hba,
        tpsa=round(tpsa, 2),
        rot_bonds=rot_bonds,
        qed=round(qed_score, 4),
        lipinski_pass=lipinski_pass,
        lipinski_violations=violations,
        has_pains=has_pains,
        sa_score=round(sa_score, 2),
    )


def _calculate_sa_score(mol: Chem.Mol) -> float:
    """Calculate synthetic accessibility score (1=easy, 10=hard).

    Uses a simplified heuristic based on fragment complexity.
    """
    try:
        from rdkit.Chem import RDConfig
        import os
        import sys
        sa_path = os.path.join(RDConfig.RDContribDir, "SA_Score")
        if sa_path not in sys.path:
            sys.path.insert(0, sa_path)
        import sascorer
        return sascorer.calculateScore(mol)
    except (ImportError, Exception):
        # Fallback: estimate from ring count + heavy atom count
        num_rings = Descriptors.RingCount(mol)
        num_heavy = mol.GetNumHeavyAtoms()
        # Rough heuristic: more complex = higher score
        score = 1.0 + (num_rings * 0.5) + (num_heavy * 0.05)
        return min(score, 10.0)


def _traffic_light(tier1: AdmetTier1) -> tuple[str, str]:
    """Assign GREEN/AMBER/RED traffic light and recommendation."""
    sa_easy = tier1.sa_score < 4

    if not tier1.lipinski_pass:
        return "RED", "not_recommended"

    if tier1.lipinski_pass and not tier1.has_pains and tier1.qed > 0.4 and sa_easy:
        return "GREEN", "recommended"

    if tier1.lipinski_pass:
        return "AMBER", "investigate"

    return "RED", "not_recommended"


def _generate_flags(tier1: AdmetTier1, overall: str) -> list[dict[str, str]]:
    """Generate human-readable warning/info flags."""
    flags: list[dict[str, str]] = []

    if tier1.has_pains:
        flags.append({"type": "warning", "message": "PAINS alert — possible assay interference"})

    if tier1.tpsa > 140:
        flags.append({"type": "warning", "message": "High TPSA (>140) — poor oral absorption likely"})

    if tier1.rot_bonds > 10:
        flags.append({"type": "warning", "message": "Many rotatable bonds (>10) — reduced oral bioavailability"})

    for v in tier1.lipinski_violations:
        flags.append({"type": "warning", "message": f"Lipinski violation: {v}"})

    if tier1.sa_score >= 6:
        flags.append({"type": "warning", "message": f"Difficult to synthesize (SA score: {tier1.sa_score})"})

    if tier1.qed > 0.7:
        flags.append({"type": "info", "message": f"High drug-likeness (QED: {tier1.qed})"})

    if tier1.tpsa < 60:
        flags.append({"type": "info", "message": "Low TPSA — may be CNS penetrant"})

    return flags

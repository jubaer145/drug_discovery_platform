import re
import logging

import httpx

from core.config import settings
from models.schemas import TargetLookupInput, PDBStructureInfo
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

# UniProt accession pattern: e.g. P00533, Q9Y2R2, A0A0C5B5G6
_UNIPROT_RE = re.compile(
    r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
)

# PDB IDs: 4 characters, first is a digit (e.g. 1IEP, 6LU7)
_PDB_ID_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")

TIMEOUT = 30.0


class TargetLookupModule(BaseModule):
    """Fetches protein data from PDB, UniProt, and AlphaFold."""

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, TargetLookupInput):
            return False, "Input must be TargetLookupInput"
        query = input.query.strip()
        if not query:
            return False, "Query must not be empty"
        if len(query) > 200:
            return False, "Query must be at most 200 characters"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, TargetLookupInput)
        query = input.query.strip()
        query_type = self._detect_query_type(query) if input.query_type == "auto" else input.query_type

        with httpx.Client(timeout=TIMEOUT) as client:
            if query_type == "pdb_id":
                return self._lookup_pdb(client, query.upper(), input.job_id)
            elif query_type == "uniprot":
                return self._lookup_uniprot(client, query.upper(), input.job_id)
            else:
                return self._search_by_name(client, query, input.job_id)

    # ------------------------------------------------------------------
    # Query type detection
    # ------------------------------------------------------------------

    def _detect_query_type(self, query: str) -> str:
        q = query.strip()
        if _PDB_ID_RE.match(q):
            return "pdb_id"
        if _UNIPROT_RE.match(q.upper()):
            return "uniprot"
        return "name"

    # ------------------------------------------------------------------
    # PDB lookup
    # ------------------------------------------------------------------

    def _lookup_pdb(self, client: httpx.Client, pdb_id: str, job_id: str) -> ModuleOutput:
        warnings: list[str] = []
        base = settings.pdb_api_url

        try:
            entry_resp = client.get(f"{base}/core/entry/{pdb_id}")
            entry_resp.raise_for_status()
            entry = entry_resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ModuleOutput(
                    job_id=job_id, status="completed", data={},
                    warnings=[f"PDB ID '{pdb_id}' not found"],
                )
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=[f"PDB API error: {e}"])
        except httpx.TimeoutException:
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=["PDB API timed out"])

        # Extract basic info from entry
        title = entry.get("struct", {}).get("title", "Unknown")
        method_list = entry.get("exptl", [])
        method = method_list[0].get("method", "Unknown") if method_list else "Unknown"
        resolution = None
        refine = entry.get("refine", [])
        if refine:
            resolution = refine[0].get("ls_d_res_high")
            if resolution is not None:
                resolution = float(resolution)

        # Try to get polymer entity for protein name and UniProt mapping
        uniprot_id = None
        gene_symbol = None
        organism = None
        try:
            poly_resp = client.get(f"{base}/core/polymer_entity/{pdb_id}/1")
            poly_resp.raise_for_status()
            poly = poly_resp.json()
            organism = (poly.get("rcsb_entity_source_organism") or [{}])[0].get("ncbi_scientific_name")

            # UniProt accessions from polymer entity
            uniprot_refs = poly.get("rcsb_polymer_entity_container_identifiers", {}).get("uniprot_ids", [])
            if uniprot_refs:
                uniprot_id = uniprot_refs[0]
        except (httpx.HTTPStatusError, httpx.TimeoutException):
            warnings.append("Could not fetch polymer entity details")

        pdb_info = PDBStructureInfo(
            pdb_id=pdb_id,
            resolution=resolution,
            method=method,
        )

        data = {
            "protein_name": title,
            "gene_symbol": gene_symbol,
            "uniprot_id": uniprot_id,
            "organism": organism,
            "pdb_structures": [pdb_info.model_dump()],
            "best_pdb_id": pdb_id,
            "total_pdb_count": 1,
            "has_alphafold": False,
            "alphafold_url": None,
        }

        # Enrich with UniProt data if we found an accession
        if uniprot_id:
            self._enrich_from_uniprot(client, uniprot_id, data, warnings)
            self._check_alphafold(client, uniprot_id, data, warnings)

        return ModuleOutput(job_id=job_id, status="completed", data=data, warnings=warnings)

    # ------------------------------------------------------------------
    # UniProt lookup
    # ------------------------------------------------------------------

    def _lookup_uniprot(self, client: httpx.Client, accession: str, job_id: str) -> ModuleOutput:
        warnings: list[str] = []
        url = f"{settings.uniprot_api_url}/{accession}.json"

        try:
            resp = client.get(url)
            resp.raise_for_status()
            entry = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ModuleOutput(
                    job_id=job_id, status="completed", data={},
                    warnings=[f"UniProt accession '{accession}' not found"],
                )
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=[f"UniProt API error: {e}"])
        except httpx.TimeoutException:
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=["UniProt API timed out"])

        data = self._parse_uniprot_entry(entry, accession)

        # Fetch PDB cross-references
        pdb_xrefs = [
            x for x in entry.get("uniProtKBCrossReferences", [])
            if x.get("database") == "PDB"
        ]
        pdb_structures = []
        for xref in pdb_xrefs[:20]:  # Limit to first 20
            props = {p["key"]: p["value"] for p in xref.get("properties", [])}
            resolution_str = props.get("Resolution", "")
            resolution = None
            if resolution_str and resolution_str.replace(".", "").replace(" A", "").isdigit():
                try:
                    resolution = float(resolution_str.replace(" A", ""))
                except ValueError:
                    pass
            pdb_structures.append(PDBStructureInfo(
                pdb_id=xref["id"],
                resolution=resolution,
                method=props.get("Method"),
            ).model_dump())

        data["pdb_structures"] = pdb_structures
        data["total_pdb_count"] = len(pdb_xrefs)

        # Find best resolution X-ray structure
        xray = [s for s in pdb_structures if s.get("method") and "ray" in s["method"].lower() and s.get("resolution")]
        if xray:
            best = min(xray, key=lambda s: s["resolution"])
            data["best_pdb_id"] = best["pdb_id"]
        elif pdb_structures:
            data["best_pdb_id"] = pdb_structures[0]["pdb_id"]

        self._check_alphafold(client, accession, data, warnings)

        return ModuleOutput(job_id=job_id, status="completed", data=data, warnings=warnings)

    # ------------------------------------------------------------------
    # Name / disease search
    # ------------------------------------------------------------------

    def _search_by_name(self, client: httpx.Client, query: str, job_id: str) -> ModuleOutput:
        warnings: list[str] = []
        url = f"{settings.uniprot_api_url}/search"
        params = {
            "query": f"{query} AND reviewed:true AND organism_id:9606",
            "format": "json",
            "size": "5",
        }

        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except httpx.HTTPStatusError as e:
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=[f"UniProt search error: {e}"])
        except httpx.TimeoutException:
            return ModuleOutput(job_id=job_id, status="failed", data={}, errors=["UniProt search timed out"])

        if not results:
            return ModuleOutput(
                job_id=job_id, status="completed", data={},
                warnings=[f"No results found for '{query}'"],
            )

        # If we found exactly 1, or the top hit is a strong match, return full data
        top = results[0]
        accession = top.get("primaryAccession", "")
        data = self._parse_uniprot_entry(top, accession)

        # If multiple candidates, include them for user selection
        if len(results) > 1:
            candidates = []
            for r in results:
                acc = r.get("primaryAccession", "")
                desc = r.get("proteinDescription", {})
                rec_name = desc.get("recommendedName", {}).get("fullName", {}).get("value", "")
                genes = r.get("genes", [])
                gene = genes[0].get("geneName", {}).get("value", "") if genes else ""
                org = r.get("organism", {}).get("scientificName", "")
                candidates.append({
                    "uniprot_id": acc,
                    "protein_name": rec_name,
                    "gene_symbol": gene,
                    "organism": org,
                })
            data["multiple_candidates"] = candidates

        # Fetch PDB cross-references for the top hit
        pdb_xrefs = [
            x for x in top.get("uniProtKBCrossReferences", [])
            if x.get("database") == "PDB"
        ]
        pdb_structures = []
        for xref in pdb_xrefs[:20]:
            props = {p["key"]: p["value"] for p in xref.get("properties", [])}
            resolution_str = props.get("Resolution", "")
            resolution = None
            if resolution_str:
                try:
                    resolution = float(resolution_str.replace(" A", "").strip())
                except ValueError:
                    pass
            pdb_structures.append(PDBStructureInfo(
                pdb_id=xref["id"],
                resolution=resolution,
                method=props.get("Method"),
            ).model_dump())

        data["pdb_structures"] = pdb_structures
        data["total_pdb_count"] = len(pdb_xrefs)

        xray = [s for s in pdb_structures if s.get("method") and "ray" in s["method"].lower() and s.get("resolution")]
        if xray:
            best = min(xray, key=lambda s: s["resolution"])
            data["best_pdb_id"] = best["pdb_id"]
        elif pdb_structures:
            data["best_pdb_id"] = pdb_structures[0]["pdb_id"]

        self._check_alphafold(client, accession, data, warnings)

        return ModuleOutput(job_id=job_id, status="completed", data=data, warnings=warnings)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_uniprot_entry(self, entry: dict, accession: str) -> dict:
        """Extract structured data from a UniProt JSON entry."""
        desc = entry.get("proteinDescription", {})
        rec_name = desc.get("recommendedName", {}).get("fullName", {}).get("value", "")
        if not rec_name:
            sub_names = desc.get("submissionNames", [])
            rec_name = sub_names[0].get("fullName", {}).get("value", "") if sub_names else "Unknown"

        genes = entry.get("genes", [])
        gene_symbol = genes[0].get("geneName", {}).get("value", "") if genes else None

        organism = entry.get("organism", {}).get("scientificName", "")

        sequence_info = entry.get("sequence", {})
        sequence_length = sequence_info.get("length")
        sequence_value = sequence_info.get("value")

        # Function summary from comments
        function_summary = None
        disease_associations = []
        for comment in entry.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    function_summary = texts[0].get("value", "")
            if comment.get("commentType") == "DISEASE":
                disease = comment.get("disease", {})
                disease_name = disease.get("diseaseId")
                if disease_name:
                    disease_associations.append(disease_name)

        return {
            "protein_name": rec_name,
            "gene_symbol": gene_symbol,
            "uniprot_id": accession,
            "organism": organism,
            "sequence_length": sequence_length,
            "sequence": sequence_value,
            "function_summary": function_summary,
            "disease_associations": disease_associations,
            "pdb_structures": [],
            "best_pdb_id": None,
            "total_pdb_count": 0,
            "has_alphafold": False,
            "alphafold_url": None,
            "multiple_candidates": None,
        }

    def _enrich_from_uniprot(self, client: httpx.Client, accession: str, data: dict, warnings: list[str]) -> None:
        """Enrich data dict with UniProt info for a given accession."""
        url = f"{settings.uniprot_api_url}/{accession}.json"
        try:
            resp = client.get(url)
            resp.raise_for_status()
            entry = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException):
            warnings.append(f"Could not fetch UniProt data for {accession}")
            return

        parsed = self._parse_uniprot_entry(entry, accession)
        data["gene_symbol"] = parsed["gene_symbol"]
        data["function_summary"] = parsed["function_summary"]
        data["disease_associations"] = parsed["disease_associations"]
        data["sequence_length"] = parsed["sequence_length"]
        data["sequence"] = parsed["sequence"]
        data["organism"] = data["organism"] or parsed["organism"]

    def _check_alphafold(self, client: httpx.Client, uniprot_id: str, data: dict, warnings: list[str]) -> None:
        """Check if an AlphaFold prediction exists for this UniProt accession."""
        url = f"{settings.alphafold_db_url}/prediction/{uniprot_id}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                data["has_alphafold"] = True
                data["alphafold_url"] = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
        except (httpx.HTTPStatusError, httpx.TimeoutException):
            warnings.append("Could not check AlphaFold availability")

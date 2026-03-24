from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://admin:secret@localhost:5432/drugdiscovery"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    esmfold_api_url: str = "https://api.esmatlas.com/foldSequence/v1/pdb/"
    alphafold_db_url: str = "https://alphafold.ebi.ac.uk/api"
    pdb_api_url: str = "https://data.rcsb.org/rest/v1"
    uniprot_api_url: str = "https://rest.uniprot.org/uniprotkb"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()

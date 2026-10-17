from pydantic import BaseModel, Field


class JobListing(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    address: str = ""
    salary: str = ""
    job_type: str = ""
    posted: str = ""
    link: str = ""
    description: str = Field(default="", max_length=500)

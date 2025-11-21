"""
Database Schemas for MemeWiki

Each Pydantic model represents a MongoDB collection.
Class name lowercased is used as the collection name.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

class Meme(BaseModel):
    """
    Meme documents
    Collection: "meme"
    """
    title: str = Field(..., description="Meme title or catchphrase")
    image_url: Optional[HttpUrl] = Field(None, description="Direct link to the meme image/gif/video thumbnail")
    caption: Optional[str] = Field(None, description="Short description or punchline")
    origin_summary: Optional[str] = Field(None, description="Where it came from, who posted first, cultural context")
    first_seen_at: Optional[str] = Field(None, description="Approx date or year first seen, e.g., '2013' or '2013-06'")
    sources: List[HttpUrl] = Field(default_factory=list, description="Source links: original post, KnowYourMeme, Wikipedia, etc.")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    submitter: Optional[str] = Field(None, description="Name or handle of the person who submitted")
    upvotes: int = Field(0, ge=0, description="Number of upvotes")
    downvotes: int = Field(0, ge=0, description="Number of downvotes")

class Comment(BaseModel):
    """
    Comments on memes
    Collection: "comment"
    """
    meme_id: str = Field(..., description="Referenced meme ObjectId as string")
    author: Optional[str] = Field(None, description="Who commented")
    text: str = Field(..., description="Comment body")
    created_at: Optional[datetime] = None

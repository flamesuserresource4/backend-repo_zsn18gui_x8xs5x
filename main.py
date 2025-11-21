import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Meme, Comment

app = FastAPI(title="MemeWiki API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo docs to JSON-friendly

def to_json(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if isinstance(doc.get("_id"), ObjectId):
        doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/")
def read_root():
    return {"message": "MemeWiki backend ready"}


# Schemas endpoint for admin tools
@app.get("/schema")
def get_schema():
    return {
        "meme": Meme.model_json_schema(),
        "comment": Comment.model_json_schema(),
    }


# Meme Endpoints
@app.post("/api/memes", response_model=dict)
def create_meme(meme: Meme):
    try:
        inserted_id = create_document("meme", meme)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MemeQuery(BaseModel):
    q: Optional[str] = None
    tag: Optional[str] = None
    limit: int = 50


@app.get("/api/memes", response_model=List[dict])
def list_memes(q: Optional[str] = None, tag: Optional[str] = None, limit: int = 50):
    try:
        filter_dict = {}
        if q:
            # Simple regex search on title or caption
            filter_dict["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"caption": {"$regex": q, "$options": "i"}},
                {"origin_summary": {"$regex": q, "$options": "i"}},
            ]
        if tag:
            filter_dict["tags"] = {"$in": [tag]}
        docs = get_documents("meme", filter_dict, limit)
        return [to_json(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memes/{meme_id}", response_model=dict)
def get_meme(meme_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["meme"].find_one({"_id": ObjectId(meme_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Meme not found")
        # Fetch comments
        comments = list(db["comment"].find({"meme_id": meme_id}).sort("created_at", -1))
        meme_json = to_json(doc)
        meme_json["comments"] = [to_json(c) for c in comments]
        return meme_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Voting
class VoteBody(BaseModel):
    direction: str  # "up" or "down"


@app.post("/api/memes/{meme_id}/vote")
def vote_meme(meme_id: str, body: VoteBody):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if body.direction not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid direction")
    inc = {"upvotes": 1} if body.direction == "up" else {"downvotes": 1}
    res = db["meme"].update_one({"_id": ObjectId(meme_id)}, {"$inc": inc, "$set": {"updated_at": None}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Meme not found")
    return {"ok": True}


# Comments
@app.post("/api/memes/{meme_id}/comments")
def add_comment(meme_id: str, comment: Comment):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Ensure meme exists
    if not db["meme"].find_one({"_id": ObjectId(meme_id)}):
        raise HTTPException(status_code=404, detail="Meme not found")
    data = comment.model_dump()
    data["meme_id"] = meme_id
    inserted_id = create_document("comment", data)
    return {"id": inserted_id}


# Test endpoint for DB
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""Dry run by default. Schedule only a reviewed ChickenFarm export."""
import argparse, datetime as dt, hashlib, json, os, urllib.request, urllib.parse
from pathlib import Path
TARGET="chicken.farm107"
ROOT=Path(__file__).resolve().parent
def request(query,variables=None):
    key=os.environ.get("BUFFER_API_KEY")
    if not key: raise RuntimeError("Private BUFFER_API_KEY is required")
    req=urllib.request.Request("https://api.buffer.com",data=json.dumps({"query":query,"variables":variables or {}}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
    with urllib.request.urlopen(req,timeout=45) as r: result=json.load(r)
    if result.get("errors"): raise RuntimeError(str(result["errors"]))
    return result["data"]
def channel():
    found=[]
    for org in request("query {account {organizations {id}}}")["account"]["organizations"]:
        for c in request("query($id:ID!){channels(input:{organizationId:$id}){id name service isQueuePaused}}",{"id":org["id"]})["channels"]:
            if c["service"].lower()=="tiktok" and c["name"].strip().lstrip("@").lower()==TARGET: found.append((org["id"],c))
    if len(found)!=1: raise RuntimeError("Exactly one matching ChickenFarm channel required; no publication")
    if found[0][1].get("isQueuePaused"): raise RuntimeError("Queue paused")
    return found[0]
def ensure_unique(oid,cid,caption,due):
    after=None
    while True:
        q="query($oid:ID!,$cid:ID!,$after:String){posts(first:50,after:$after,input:{organizationId:$oid,filter:{channelIds:[$cid]}}){edges{node{id text dueAt}} pageInfo{hasNextPage endCursor}}}"
        data=request(q,{"oid":oid,"cid":cid,"after":after})["posts"]
        for e in data["edges"]:
            p=e["node"]
            if p["text"]==caption: raise RuntimeError("Duplicate caption")
            if p.get("dueAt") and dt.datetime.fromisoformat(p["dueAt"].replace("Z","+00:00"))==due: raise RuntimeError("Time occupied")
        if not data["pageInfo"]["hasNextPage"]: return
        new=data["pageInfo"]["endCursor"]
        if not new or new==after: raise RuntimeError("Pagination failed")
        after=new
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--id",required=True,choices=["silkie","rooster"])
    p.add_argument("--url",required=True)
    p.add_argument("--due",required=True)
    p.add_argument("--reviewed",action="store_true")
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    due=dt.datetime.fromisoformat(a.due.replace("Z","+00:00"))
    if due.tzinfo is None or due<=dt.datetime.now(dt.timezone.utc): p.error("Future timezone-aware date required")
    due=due.astimezone(dt.timezone.utc)
    folder=ROOT/"output"
    manifest=json.loads((folder/(a.id+".json")).read_text())
    video=folder/(a.id+".mp4")
    caption=(folder/(a.id+".txt")).read_text()
    if not a.reviewed or manifest.get("technical_QA")!="passed" or manifest.get("source",{}).get("id")!=a.id: raise RuntimeError("Technical and human review required")
    expected=manifest["sha256"]
    if hashlib.sha256(video.read_bytes()).hexdigest()!=expected: raise RuntimeError("Local hash mismatch")
    if urllib.parse.urlparse(a.url).scheme!="https": raise RuntimeError("HTTPS media required")
    sha=hashlib.sha256();size=0
    with urllib.request.urlopen(a.url,timeout=60) as r:
        while chunk:=r.read(1024*1024):
            size+=len(chunk)
            if size>video.stat().st_size: raise RuntimeError("Remote size mismatch")
            sha.update(chunk)
    if sha.hexdigest()!=expected: raise RuntimeError("Remote file differs from reviewed file")
    oid,c=channel();ensure_unique(oid,c["id"],caption,due)
    if not a.execute: print("Dry run passed; no post created");return
    inp={"text":caption,"channelId":c["id"],"schedulingType":"automatic","mode":"customScheduled","dueAt":due.isoformat().replace("+00:00","Z"),"assets":[{"video":{"url":a.url}}]}
    q="mutation($input:CreatePostInput!){createPost(input:$input){... on PostActionSuccess{post{id channelId dueAt status}} ... on MutationError{message}}}"
    res=request(q,{"input":inp})["createPost"];post=res.get("post")
    if not post or post.get("channelId")!=c["id"]: raise RuntimeError("No verified scheduling result; inspect before retrying")
    print(json.dumps(post,ensure_ascii=False))
    print("Verify published TikTok URL after due time.")
if __name__=="__main__":main()

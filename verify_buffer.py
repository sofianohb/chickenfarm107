"""Read-only verification; never print tokens, IDs, other accounts, or response bodies."""
import os,json,urllib.request,sys
TARGET="chicken.farm107"
def query(q,variables=None):
    key=os.environ.get("BUFFER_API_KEY","")
    if not key: raise RuntimeError("MISSING_SECRET")
    req=urllib.request.Request("https://api.buffer.com",data=json.dumps({"query":q,"variables":variables or {}}).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as response: obj=json.load(response)
    if obj.get("errors"): raise RuntimeError("BUFFER_GRAPHQL_ERROR")
    return obj["data"]
def main():
    if not os.environ.get("BUFFER_API_KEY"):
        print("MISSING_SECRET: add BUFFER_API_KEY through repository Actions secrets.");return 2
    try:
        orgs=query("query { account { organizations { id } } }")["account"]["organizations"]
        count=0
        for org in orgs:
            channels=query("query($id: ID!) { channels(input: { organizationId: $id }) { name service } }",{"id":org["id"]})["channels"]
            for c in channels:
                if c["service"].lower()=="tiktok" and c["name"].strip().lstrip("@").lower()==TARGET: count+=1
        if count!=1:
            print("TARGET_NOT_UNIQUE_OR_NOT_CONNECTED: no publication.");return 3
        print("VERIFIED: exactly one TikTok @chicken.farm107 channel. Read-only test; no posts created.")
        return 0
    except Exception:
        print("CHECK_FAILED: verify key permissions or Buffer API availability. No posts created.");return 4
if __name__=="__main__":sys.exit(main())

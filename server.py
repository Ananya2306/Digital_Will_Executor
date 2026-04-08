import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Digital Will Executor", version="1.0.0")

SCENARIOS = {"easy":[{"id":"easy_001","will_text":"Delete all my social media accounts. Transfer my photos and videos to my daughter Sarah. Cancel all subscriptions.","beneficiaries":["Sarah"],"executor":"Sarah","assets":[{"id":"instagram","platform":"Instagram","category":"social","has_monetary_value":False,"is_private":False,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"facebook","platform":"Facebook","category":"social","has_monetary_value":False,"is_private":False,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"google_photos","platform":"Google Photos","category":"storage","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":True},{"id":"spotify","platform":"Spotify","category":"subscription","has_monetary_value":False,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":False},{"id":"netflix","platform":"Netflix","category":"subscription","has_monetary_value":False,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":False}],"gold_actions":{"instagram":"delete_permanently","facebook":"delete_permanently","google_photos":"transfer_to_beneficiary","spotify":"cancel_subscription","netflix":"cancel_subscription"}}],"medium":[{"id":"medium_001","will_text":"Give my online stuff to my kids. They should have what's useful.","beneficiaries":["kid_1","kid_2"],"executor":"kid_1","assets":[{"id":"netflix","platform":"Netflix","category":"subscription","has_monetary_value":False,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":False},{"id":"crypto_wallet","platform":"Coinbase","category":"financial","has_monetary_value":True,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"work_slack","platform":"Slack (Work)","category":"professional","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"journal_blog","platform":"Personal Blog","category":"personal","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"github","platform":"GitHub","category":"professional","has_monetary_value":False,"is_private":False,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"google_drive","platform":"Google Drive","category":"storage","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":True}],"gold_actions":{"netflix":"transfer_to_beneficiary","crypto_wallet":"transfer_to_beneficiary","work_slack":"archive_and_hold","journal_blog":"preserve_memorialize","github":"transfer_to_beneficiary","google_drive":"transfer_to_beneficiary"}}],"hard":[{"id":"hard_001","will_text":"My daughter Priya gets everything digital. She is my heir.","beneficiaries":["Priya","Rahul"],"executor":"Rahul","conflict_note":"Son Rahul is listed as executor but daughter Priya is listed as heir. Business email active with clients. Secret secondary email discovered.","assets":[{"id":"primary_gmail","platform":"Gmail (Personal)","category":"personal","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":True},{"id":"business_email","platform":"Gmail (Business)","category":"professional","has_monetary_value":True,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":True},{"id":"secret_email","platform":"ProtonMail","category":"personal","has_monetary_value":False,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"crypto_portfolio","platform":"Binance","category":"financial","has_monetary_value":True,"is_private":True,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"aws_account","platform":"AWS","category":"professional","has_monetary_value":True,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":True},{"id":"icloud","platform":"iCloud","category":"storage","has_monetary_value":False,"is_private":True,"has_active_subscription":True,"linked_to_other_assets":False},{"id":"linkedin","platform":"LinkedIn","category":"professional","has_monetary_value":False,"is_private":False,"has_active_subscription":False,"linked_to_other_assets":False},{"id":"domain_registrar","platform":"GoDaddy","category":"financial","has_monetary_value":True,"is_private":False,"has_active_subscription":True,"linked_to_other_assets":True}],"gold_actions":{"primary_gmail":"transfer_to_beneficiary","business_email":"flag_for_human_review","secret_email":"flag_for_human_review","crypto_portfolio":"transfer_to_beneficiary","aws_account":"flag_for_human_review","icloud":"transfer_to_beneficiary","linkedin":"preserve_memorialize","domain_registrar":"flag_for_human_review"}}]}

_state: Dict[str, Any] = {}

def _init(d):
    s = SCENARIOS[d][0]
    _state[d] = {"s":s,"assets":{a["id"]:a for a in s["assets"]},"remaining":[a["id"] for a in s["assets"]],"decisions":{},"irrev":0,"step":0,"done":False,"rewards":[]}

def _obs(d):
    st=_state[d]; s=st["s"]
    return {"task_id":s["id"],"will":{"raw_text":s["will_text"],"beneficiaries":s["beneficiaries"],"executor_name":s["executor"],"conflict_note":s.get("conflict_note")},"assets":list(st["assets"].values()),"remaining_asset_ids":st["remaining"],"decisions_made":st["decisions"],"irreversible_actions_taken":st["irrev"],"step_number":st["step"]}

def _reward(asset,action,gold,conflict_note=None):
    CAT={"social":["delete_permanently","preserve_memorialize"],"financial":["transfer_to_beneficiary","flag_for_human_review"],"storage":["transfer_to_beneficiary","archive_and_hold"],"subscription":["cancel_subscription","transfer_to_beneficiary"],"professional":["archive_and_hold","flag_for_human_review"],"personal":["preserve_memorialize","flag_for_human_review"]}
    c=asset.get("category",""); m=asset.get("has_monetary_value",False); p=asset.get("is_private",False); l=asset.get("linked_to_other_assets",False)
    cor=0.4 if action==gold else (0.2 if action in CAT.get(c,[]) else 0.0)
    ia=0.0 if (m and action=="delete_permanently") else (0.3 if (m and action in ["transfer_to_beneficiary","flag_for_human_review"]) else (0.2 if (not m and action in CAT.get(c,[])) else 0.1))
    ps=0.2 if (p and action=="delete_permanently") else (0.05 if (p and action=="transfer_to_beneficiary") else 0.1)
    amb=(l and m) or (p and m) or (c=="professional" and m) or bool(conflict_note and asset["id"] in str(conflict_note))
    hb=0.1 if (amb and action=="flag_for_human_review") else (-0.1 if (not amb and action=="flag_for_human_review") else 0.0)
    pen=-0.5 if (action=="delete_permanently" and m) else (-0.3 if (action=="delete_permanently" and p and l) else 0.0)
    return round(max(0.0,min(1.0,cor+ia+ps+hb+pen)),2)

class RR(BaseModel):
    difficulty: Optional[str]="easy"
class SR(BaseModel):
    difficulty: Optional[str]="easy"; asset_id: str; action: str; reasoning: Optional[str]=""

@app.get("/health")
def health():
    return {"status":"ok","env":"digital-will-executor"}

@app.post("/reset")
def reset(req: RR):
    d=req.difficulty or "easy"
    if d not in SCENARIOS: d="easy"
    _init(d)
    return _obs(d)

@app.post("/step")
def step(req: SR):
    d=req.difficulty or "easy"
    if d not in _state: _init(d)
    st=_state[d]
    if req.asset_id not in st["assets"]:
        return {"observation":_obs(d),"reward":{"value":0.0},"done":st["done"],"info":{"error":"invalid asset_id"}}
    if req.asset_id not in st["remaining"]:
        return {"observation":_obs(d),"reward":{"value":0.0},"done":st["done"],"info":{"warning":"already processed"}}
    s=st["s"]; asset=st["assets"][req.asset_id]; gold=s["gold_actions"].get(req.asset_id,"flag_for_human_review")
    rv=_reward(asset,req.action,gold,s.get("conflict_note"))
    st["remaining"]=[x for x in st["remaining"] if x!=req.asset_id]
    st["decisions"][req.asset_id]=req.action; st["step"]+=1; st["rewards"].append(rv)
    if req.action=="delete_permanently": st["irrev"]+=1
    st["done"]=len(st["remaining"])==0
    return {"observation":_obs(d),"reward":{"value":rv},"done":st["done"],"info":{"step":st["step"],"gold_action":gold}}

@app.get("/state")
def state(difficulty: str="easy"):
    if difficulty not in _state: _init(difficulty)
    st=_state[difficulty]; r=st["rewards"]
    return {"difficulty":difficulty,"step":st["step"],"done":st["done"],"decisions_made":st["decisions"],"remaining_assets":st["remaining"],"mean_reward":round(sum(r)/len(r),3) if r else 0.0}

if __name__=="__main__":
    uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT",7860)))
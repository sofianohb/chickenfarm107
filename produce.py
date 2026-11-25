import hashlib, json, urllib.request, urllib.parse, subprocess, shutil, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCES=[
 dict(id="silkie",file="Gallus_gallus_domesticus_-_Kanagawa_2025_2_15.webm",sha1="40f5860e05dc73325ceac1540b24c253f73c7a22",author="Nesnad",license="CC BY 4.0",license_url="https://creativecommons.org/licenses/by/4.0/",title="دجاج السيلكي",subtitle="ريش ناعم بمظهر مميز",question="هل تربي هذه السلالة؟",duration=20),
 dict(id="rooster",file="Rooster_prancing,_pecking.webm",sha1="7d7206733efa07cc5069312049d23772e4ff1dd9",author="Uusijani",license="CC0 1.0",license_url="https://creativecommons.org/publicdomain/zero/1.0/",title="مشاهد من حياة الديك",subtitle="البحث عن الطعام سلوك طبيعي",question="ما أجمل ديك شاهدته؟",duration=22)]
def run(*args):
    return subprocess.check_output(args,cwd=ROOT,text=True)
def probe(path):
    return json.loads(run("ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)))
def download(s,p):
    h=hashlib.md5(s["file"].encode()).hexdigest()
    url="https://upload.wikimedia.org/wikipedia/commons/"+h[0]+"/"+h[:2]+"/"+urllib.parse.quote(s["file"])
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"ChickenFarmEditorial/1.0 (https://github.com/sofianohb/chickenfarm107)"})
            with urllib.request.urlopen(req,timeout=120) as r,p.open("wb") as f: shutil.copyfileobj(r,f)
            if hashlib.sha1(p.read_bytes()).hexdigest()!=s["sha1"]: raise ValueError("Source checksum mismatch")
            return url
        except Exception:
            p.unlink(missing_ok=True)
            if attempt==2: raise
            time.sleep(5*(attempt+1))
def produce(s):
    raw=ROOT/"raw";out=ROOT/"output";raw.mkdir(exist_ok=True);out.mkdir(exist_ok=True)
    src=raw/(s["id"]+".webm");target=out/(s["id"]+".mp4");subs=out/(s["id"]+".ass")
    url=download(s,src)
    meta=probe(src);v=next(x for x in meta["streams"] if x["codec_type"]=="video")
    assert float(meta["format"]["duration"])>=s["duration"]
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,Noto Naskh Arabic,76,&H00FFFFFF,&H00FFFFFF,&H00152C19,&H00152C19,-1,0,0,0,100,100,0,0,1,4,1,8,80,80,215,1
Style: Credit,DejaVu Sans,32,&H00FFFFFF,&H00FFFFFF,&H00152C19,&H00152C19,0,0,0,0,100,100,0,0,1,2,0,2,80,80,260,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    d=s["duration"]
    subs.write_text(header+f'Dialogue: 0,0:00:00.00,0:00:04.00,Main,,0,0,0,,{s["title"]}\nDialogue: 0,0:00:04.00,0:00:12.00,Main,,0,0,0,,{s["subtitle"]}\nDialogue: 0,0:00:12.00,0:00:{d:02d}.00,Main,,0,0,0,,{s["question"]}\nDialogue: 0,0:00:00.00,0:00:{d:02d}.00,Credit,,0,0,0,,{s["author"]} / {s["license"]} / Wikimedia Commons\n',encoding="utf8")
    vf=f"scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x152C19,setsar=1,fps=30,ass=output/{subs.name}"
    audio=any(x["codec_type"]=="audio" for x in meta["streams"])
    cmd=["ffmpeg","-nostdin","-y","-i",str(src)]
    if not audio: cmd+=["-f","lavfi","-i","anullsrc=r=48000:cl=stereo"]
    cmd+=["-map","0:v:0","-map","0:a:0" if audio else "1:a:0","-t",str(d),"-vf",vf,"-c:v","libx264","-preset","fast","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",str(target)]
    subprocess.run(cmd,cwd=ROOT,check=True)
    result=probe(target);vs=next(x for x in result["streams"] if x["codec_type"]=="video")
    assert (vs["width"],vs["height"],vs["codec_name"],vs["avg_frame_rate"])==(1080,1920,"h264","30/1")
    assert abs(float(result["format"]["duration"])-d)<0.5
    run("ffmpeg","-v","error","-xerror","-i",str(target),"-f","null","-")
    page="https://commons.wikimedia.org/wiki/File:"+urllib.parse.quote(s["file"])
    caption=f'{s["title"]} 🐓\n{s["subtitle"]}. {s["question"]}\nتصوير: {s["author"]} | {s["license"]} | {s["license_url"]}\nالمصدر: {page}\nتم القص وتنسيق الفيديو وإضافة النصوص.\n#دواجن_الزينة #دجاج #ChickenFarm'
    (out/(s["id"]+".txt")).write_text(caption,encoding="utf8")
    (out/(s["id"]+".json")).write_text(json.dumps(dict(source=s,source_url=url,source_page=page,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),technical_QA="passed",visual_and_audio_review="required before publishing",original_width=v["width"],original_height=v["height"]),ensure_ascii=False,indent=2),encoding="utf8")
    for label,sec in [("start",1),("middle",d//2),("end",d-1)]:
        run("ffmpeg","-v","error","-y","-ss",str(sec),"-i",str(target),"-frames:v","1",str(out/(s["id"]+"_"+label+".jpg")))
    print("QA passed",target,flush=True)
if __name__=="__main__":
    for s in SOURCES: produce(s)

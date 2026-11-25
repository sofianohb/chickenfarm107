"""Clean, text-free video; genuine field recordings, attribution in caption."""
import hashlib,json,urllib.request,urllib.parse,shutil,subprocess,time,re
from pathlib import Path
from produce import SOURCES,download,probe,run,ROOT
AUDIO={"silkie":("Chickens_demanding_food.ogg","e8260d842ceb7867bb6b7da26b9b4bebd6e3b7fa"),"rooster":("Medium_rooster_crowing.ogg",None)}
def produce(s):
    raw=ROOT/"raw";out=ROOT/"output";raw.mkdir(exist_ok=True);out.mkdir(exist_ok=True)
    src=raw/(s["id"]+".webm");url=download(s,src)
    name,sha=AUDIO[s["id"]]
    h=hashlib.md5(name.encode()).hexdigest()
    audio_url="https://upload.wikimedia.org/wikipedia/commons/"+h[0]+"/"+h[:2]+"/"+urllib.parse.quote(name)
    audio=raw/name
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(audio_url,headers={"User-Agent":"ChickenFarmEditorial/2.0 (https://github.com/sofianohb/chickenfarm107)"}),timeout=90) as r,audio.open("wb") as f: shutil.copyfileobj(r,f)
            if sha and hashlib.sha1(audio.read_bytes()).hexdigest()!=sha: raise ValueError("Audio checksum mismatch")
            break
        except Exception:
            audio.unlink(missing_ok=True)
            if i==2: raise
            time.sleep(4*(i+1))
    assert any(x["codec_type"]=="audio" for x in probe(audio)["streams"])
    meta=probe(src);v=next(x for x in meta["streams"] if x["codec_type"]=="video")
    d=s["duration"];assert float(meta["format"]["duration"])>=d
    target=out/(s["id"]+".mp4")
    # Full-screen 9:16 crop; preserve aspect ratio, no padding, no blur or overlays.
    # Review head/body framing at start/middle/end; reject clips that cut the bird.
    vf="[0:v]scale=1080:1920:force_original_aspect_ratio=increase:force_divisible_by=2,crop=1080:1920,setsar=1,fps=30[v]"
    af=f"volume=0.8,afade=t=in:st=0:d=0.25,afade=t=out:st={d-0.5}:d=0.5"
    subprocess.run(["ffmpeg","-nostdin","-y","-i",str(src),"-stream_loop","-1","-i",str(audio),"-filter_complex_threads","2","-filter_complex",vf,"-map","[v]","-map","1:a:0","-t",str(d),"-af",af,"-c:v","libx264","-threads","4","-preset","fast","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-movflags","+faststart",str(target)],cwd=ROOT,check=True)
    result=probe(target);vs=next(x for x in result["streams"] if x["codec_type"]=="video")
    assert (vs["width"],vs["height"],vs["codec_name"],vs["avg_frame_rate"])==(1080,1920,"h264","30/1")
    assert abs(float(result["format"]["duration"])-d)<0.5
    run("ffmpeg","-v","error","-xerror","-i",str(target),"-f","null","-")
    vol=subprocess.run(["ffmpeg","-hide_banner","-i",str(target),"-vn","-af","volumedetect","-f","null","-"],capture_output=True,text=True,check=True).stderr
    mean=float(re.search(r"mean_volume:\s*(-?[\d.]+) dB",vol).group(1));assert mean>-50
    page="https://commons.wikimedia.org/wiki/File:"+urllib.parse.quote(s["file"])
    apage="https://commons.wikimedia.org/wiki/File:"+urllib.parse.quote(name)
    caption=f'{s["title"]} 🐓\n{s["question"]}\nتصوير: {s["author"]} | {s["license"]} | {s["license_url"]}\n{page}\nصوت دواجن حقيقي مضاف من تسجيل منفصل: alys (Public domain) {apage}\nتم تنسيق الصورة وإضافة تسجيل صوتي منفصل.\n#دواجن_الزينة #دجاج #ChickenFarm'
    (out/(s["id"]+".txt")).write_text(caption,encoding="utf8")
    (out/(s["id"]+".json")).write_text(json.dumps(dict(source=s,source_url=url,source_page=page,audio_page=apage,audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),audio_license="Public domain",audio_author="alys",audio_is_separate_recording=True,mean_volume_db=mean,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),technical_QA="passed",visual_and_audio_review="required before publishing",original_width=v["width"],original_height=v["height"],text_overlay=False,framing='full_screen_9_16_center_crop',visual_framing_review='reject if bird is cut; prefer native vertical footage'),ensure_ascii=False,indent=2),encoding="utf8")
    for label,sec in [("start",1),("middle",d//2),("end",d-1)]:
        run("ffmpeg","-v","error","-y","-ss",str(sec),"-i",str(target),"-frames:v","1",str(out/(s["id"]+"_"+label+".jpg")))
    print("QA passed",target,"mean_volume",mean,flush=True)
if __name__=="__main__":
    for s in SOURCES: produce(s)

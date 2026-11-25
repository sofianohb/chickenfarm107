"""Native 9:16 only. Local review exports, not automatic publication."""
from produce import ROOT,download,probe,run
import hashlib,json,subprocess,re,urllib.parse
SOURCES=[
 {"id":"australorp_chicks","file":"Australorp_Chicks_Dust_Bathing,_Background_Australian_Magpie_Calls.webm","sha1":"b81bdeb0e92f96b1f18041ed59332f3465ca3c22","author":"100percent ballerina","license":"CC BY-SA 4.0","license_url":"https://creativecommons.org/licenses/by-sa/4.0/","title":"صيصان الأسترالوب تستحم بالتراب","sound":"الصوت الأصلي يتضمن أصوات طائر العقعق الأسترالي"},
 {"id":"hen_chicks","file":"A_mother_hen_with_chicks.webm","sha1":"c4d412f1c543595d249789dbac34d75ef2b05cc8","author":"NairobiPapel","license":"CC BY-SA 3.0","license_url":"https://creativecommons.org/licenses/by-sa/3.0/","title":"دجاجة مع صيصانها بعمر أربعة أيام","sound":"الصوت الأصلي للتسجيل؛ لا يُنسب إلى نوع طائر محدد"}
]
def main():
    raw=ROOT/"raw";out=ROOT/"output";raw.mkdir(exist_ok=True);out.mkdir(exist_ok=True)
    report=[]
    for s in SOURCES:
        src=raw/(s["id"]+".webm");dst=out/(s["id"]+".mp4")
        try:
            url=download(s,src);m=probe(src);v=next(x for x in m["streams"] if x["codec_type"]=="video")
            if (v["width"],v["height"])!=(1080,1920): raise ValueError("Not native 1080x1920")
            if not any(x["codec_type"]=="audio" for x in m["streams"]): raise ValueError("No recorded audio")
            subprocess.run(["ffmpeg","-nostdin","-y","-i",str(src),"-map","0:v:0","-map","0:a:0","-vf","setsar=1,fps=30","-c:v","libx264","-threads","4","-preset","fast","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",str(dst)],check=True)
            result=probe(dst);v2=next(x for x in result["streams"] if x["codec_type"]=="video")
            assert (v2["width"],v2["height"],v2["codec_name"],v2["avg_frame_rate"])==(1080,1920,"h264","30/1")
            assert abs(float(result["format"]["duration"])-float(m["format"]["duration"]))<0.5
            run("ffmpeg","-v","error","-xerror","-i",str(dst),"-f","null","-")
            log=subprocess.run(["ffmpeg","-hide_banner","-i",str(dst),"-vn","-af","volumedetect","-f","null","-"],capture_output=True,text=True,check=True).stderr
            mean=float(re.search(r"mean_volume:\s*(-?[\d.]+) dB",log).group(1))
            if mean<=-50: raise ValueError("Source audio silent; hold")
            d=float(result["format"]["duration"])
            page="https://commons.wikimedia.org/wiki/File:"+urllib.parse.quote(s["file"])
            (out/(s["id"]+".txt")).write_text(f'{s["title"]} 🐓\n{s["sound"]}\nتصوير: {s["author"]} | {s["license"]}\n{s["license_url"]}\n{page}\nتحويل تقني إلى MP4 و30 إطاراً؛ يبقى الترخيص نفسه.\n#دجاج #ChickenFarm',encoding="utf-8")
            for label,t in [("start",0.5),("middle",d/2),("end",d-0.5)]:
                run("ffmpeg","-v","error","-y","-ss",str(t),"-i",str(dst),"-frames:v","1",str(out/(s["id"]+"_"+label+".jpg")))
            info=dict(source=s,source_url=url,source_page=page,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),duration=d,mean_volume_db=mean,native_vertical=True,text_overlay=False,technical_QA="passed",publication="HOLD: visual/audio review and share-alike platform compatibility required")
            (out/(s["id"]+".json")).write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
            report.append({"id":s["id"],"status":"technical_pass_review_only"})
        except Exception as e:
            dst.unlink(missing_ok=True);report.append({"id":s["id"],"status":"rejected","reason":str(e)})
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    if not any(x["status"]=="technical_pass_review_only" for x in report): raise SystemExit(1)
if __name__=="__main__":main()

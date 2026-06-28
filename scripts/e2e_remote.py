import json, os, urllib.request, urllib.error, subprocess, shutil, pathlib, tempfile
base="http://127.0.0.1:8090"
def read_env_token(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        return subprocess.check_output(f"sudo -n grep '^{name}=' /opt/sc4s-manager/manager.env | cut -d= -f2-", shell=True, text=True).strip()
    except subprocess.CalledProcessError:
        return ""
manual_token=read_env_token("SC4S_MANAGER_MANUAL_LOGIN_TOKEN")
api_token=read_env_token("SC4S_MANAGER_API_TOKEN")
H={"Content-Type":"application/json","X-Authentik-Username":"qa.e2e"}
if manual_token:
    H["Authorization"]="Bearer "+manual_token
elif api_token:
    H["X-SC4S-Manager-Token"]=api_token
else:
    raise SystemExit("SC4S_MANAGER_MANUAL_LOGIN_TOKEN or SC4S_MANAGER_API_TOKEN is required")
def req(method,path,data=None,headers=None):
    h=dict(H if headers is None else headers)
    body=None if data is None else json.dumps(data).encode()
    r=urllib.request.Request(base+path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            txt=resp.read().decode()
            try: obj=json.loads(txt) if txt else None
            except Exception: obj=None
            return resp.status, txt, obj
    except urllib.error.HTTPError as e:
        txt=e.read().decode()
        try: obj=json.loads(txt)
        except Exception: obj=None
        return e.code, txt, obj
root=pathlib.Path("/opt/sc4s")
backup_dir=pathlib.Path(tempfile.mkdtemp(prefix="sc4s-manager-e2e-"))
backup_files=["env_file","local/context/vendor_product_by_source.csv","local/context/splunk_metadata.csv","local/context/compliance_meta_by_source.csv"]
for f in backup_files:
    p=root/f
    if p.exists(): shutil.copy2(p, backup_dir / f.replace('/','__'))
created=[]
results=[]
def check(name, cond, detail):
    results.append((name, bool(cond), detail))
try:
    for path in ["/health","/api/health","/api/stats","/api/config","/api/templates","/api/products","/api/audit","/api/tls","/api/schema","/api/metrics/syslog-ng","/api/backups","/api/validate"]:
        code,txt,obj=req("GET",path)
        check("GET "+path, code==200, code)
    code,txt,obj=req("GET","/api/config/file?path=../env_file")
    check("path traversal GET returns 400", code==400, code)
    code,txt,obj=req("POST","/api/env", {"key":"SC4S_MANAGER_API_TOKEN","value":"bad"})
    check("secret env edit rejected", code==400, code)
    code,txt,obj=req("POST","/api/ports", {"kind":"udp","enabled":True,"port":70000})
    check("invalid port rejected", code==400, code)
    testfile="config/filters/e2e_manager_smoke.conf"
    code,txt,obj=req("POST","/api/config/file", {"path":testfile,"content":"# e2e smoke\n"})
    check("config file save", code==200, code)
    created.append(root/"local"/testfile)
    code,txt,obj=req("GET","/api/config/file?path="+urllib.request.quote(testfile))
    check("config file readback", code==200 and "e2e smoke" in txt, code)
    code,txt,obj=req("POST","/api/services", {"filter":"e2e_mgr_smoke","source":"192.0.2.44","vendor_product":"test_product","index":"osnix","compliance":"qa"})
    check("add service", code==200, code)
    created.append(root/"local/config/filters/e2e_mgr_smoke.conf")
    code,txt,obj=req("POST","/api/templates/export", {"name":"e2e-smoke"})
    check("template export", code==200 and obj and pathlib.Path(obj.get("template","")).exists(), code)
    if obj and obj.get("template"): created.append(pathlib.Path(obj["template"]))
    code,txt,obj=req("POST","/api/products/export", {"name":"e2e-products"})
    check("products export alias", code==200, code)
    if obj and obj.get("template"): created.append(pathlib.Path(obj["template"]))
    code,txt,obj=req("GET","/metrics")
    check("prometheus metrics", code==200 and "sc4s_manager_syslogng" in txt, code)
    code,txt,obj=req("POST","/api/env/secret", {"key":"SC4S_QA_E2E_TOKEN","value":"temporary-e2e-secret"})
    check("secret env update redacted", code==200 and obj and obj.get("value")=="[REDACTED]", code)
    code,txt,obj=req("GET","/api/backups")
    newest=(obj.get("backups") or [{}])[0].get("name") if obj else ""
    code2,txt2,obj2=req("GET","/api/backups/diff?name="+urllib.request.quote(newest)) if newest else (0,"",None)
    check("backup diff redacted", code2==200 and "temporary-e2e-secret" not in txt2, code2)
    code,txt,obj=req("POST","/api/templates/import", {"path":"/tmp/not-allowed.zip"})
    check("unsafe template import rejected", code==400, code)
finally:
    for f in backup_files:
        src=backup_dir / f.replace('/','__')
        dst=root/f
        if src.exists(): shutil.copy2(src,dst)
    for p in created:
        try:
            if p.exists(): p.unlink()
        except Exception: pass
    shutil.rmtree(backup_dir, ignore_errors=True)
print(json.dumps({"passed":sum(1 for _,ok,_ in results if ok),"total":len(results),"results":results}, indent=2))

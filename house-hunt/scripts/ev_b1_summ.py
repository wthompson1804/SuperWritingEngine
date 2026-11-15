import json,re,sys,csv
sys.path.insert(0,"scripts")
import h_apartmentlist as al
d=json.load(open("raw/evidence_b1/al_listings.json"))
rows={r["addr_key"]:r for r in csv.DictReader(open("data/reference/evidence_batches/batch_1.csv"))}
summ={}
for k,v in d.items():
    L=v.get("listing")
    if not L: print(k,"NO LISTING",v.get("error")); continue
    r=rows[k]
    fl=al.flight(open(v["raw_path"]).read())
    stored=dict(zip([x.strip() for x in r["unit_list"].split(",")],[x.strip() for x in r["rents"].split(",")]))
    units=[]
    for fp in L["available_units"]:
        for u in fp.get("units") or []:
            units.append(dict(unit=u.get("name") or u.get("unit_number") or u.get("display_name"),bed=fp["bed"],price=u.get("price"),base=u.get("base_price"),on=u.get("available_on"),now=u.get("available_now"),sqft=u.get("sqft"),floor=u.get("floor"),raw={kk:vv for kk,vv in u.items() if kk not in("photos",)}))
    am=al.amen_names(L,"community_amenities")+al.amen_names(L,"unit_amenities")+al.amen_names(L,"top_amenities")
    rs=re.search(r'"reviewSummary":(\{[^}]*\})',fl)
    revs=[]
    for m in re.finditer(r'"reviews":\[',fl):
        try: o,_=al.DEC.raw_decode(fl,m.end()-1); revs=o if len(o)>len(revs) else revs
        except Exception: pass
    s=dict(name=L["display_name"],url=v["url"],at=v["retrieved_at"],stored=stored,units=units,pets=L.get("pet_policies"),elevator="Elevator" in am,amen=sorted(set(am)),parking=L.get("parking"),parking_text=L.get("parking_details_text"),year=L.get("year_built"),site=L.get("website_url"),pmc=L.get("pmc_display_name"),source=L.get("source_name"),total_units=L.get("total_units_count"),fees=L.get("fees"),addfees=L.get("additional_fees_text"),util=L.get("utilities_included_text"),specials=L.get("specials"),desc=L.get("description"),review_summary=json.loads(rs.group(1)) if rs else None,reviews=revs,active=L.get("active"),updated=L.get("updated_at"),checked=L.get("availability_last_checked_at"))
    summ[k]=s
json.dump(summ,open("raw/evidence_b1/al_summary.json","w"),indent=1)
for k,s in summ.items():
    print("==",k,"|",s["name"],"| elev",s["elevator"],"| yr",s["year"],"| pmc",s["pmc"],"| src",s["source"],"| tot",s["total_units"],"| active",s["active"],s["checked"])
    print("   site:",(s["site"] or "")[:90])
    for un,pr in s["stored"].items():
        hit=[u for u in s["units"] if str(u["unit"])==un]
        print("   stored",un,pr,"->",[(u["price"],u["base"],u["on"],u["now"],u["floor"],u["bed"]) for u in hit] or "GONE")
    ok=[u for u in s["units"] if u["bed"]<=1 and (u["price"] or 9e9)<=3000]
    print("   other<=3000 studio/1BR:",len(ok),[(u["unit"],u["price"],u["on"]) for u in ok][:8])
    p=s["pets"] or {}
    print("   pets:",json.dumps({kk:vv for kk,vv in p.items() if kk!="cats"})[:400])
    print("   parking:",json.dumps(s["parking"])[:300],s["parking_text"])
    print("   fees:",s["fees"],s["addfees"],"| util:",s["util"])
    print("   revsum:",json.dumps(s["review_summary"])[:400],"| nrev",len(s["reviews"]))

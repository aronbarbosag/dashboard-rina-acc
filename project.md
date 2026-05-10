
POST / https://api.rinaacc.com.br/login  (LOGIN)
{
  "login":"aron.barbosa",
  "password":"Estrela32."
}

{{token}}



POST / https://api.rinaacc.com.br/search  (DADOS DA AUDITORIA)

Authorization:{{token}}

{

"base":["AJU","BEL","BJP","CFB","CAW","SNAO","CIZ","FST","FOR","GIG","GMR","ITA","JPA","MCP","MEA","MAO","MRC","OIA","PRC","PUC","RAO","SSA","TST","VIX"],"operator":["AEROLEO","AZUL","BRISTOW","CHC","CDS","FOTOTERRA","LIDER","OMNI","RICO","TOTAL","TREINAMENTO","VOE"],"aircraftPrefix":["PP-NLX","PR-AEH","PR-AEK","PR-AEV","PR-AIE","PR-AIF","PR-AIG","PR-AQH","PR-AQJ","PR-AQZ","PR-BGB","PR-BGC","PR-BGG","PR-BGJ","PR-BGM","PR-BGN","PR-BGP","PR-BGQ","PR-BGT","PR-BGU","PR-BGX","PR-BGY","PR-BGZ","PR-CDV","PR-CFX","PR-CGD","PR-CGE","PR-CGF","PR-CGH","PR-CGJ","PR-CGK","PR-CGN","PR-CGO","PR-CGP","PR-CGS","PR-CGT","PR-CGU","PR-CGW","PR-CHA","PR-CHC","PR-CHD","PR-CHE","PR-CHG","PR-CHI","PR-CHQ","PR-CHS","PR-CHT","PR-CPV","PR-CPX","PR-EFX","PR-EPV","PR-JAA","PR-JAR","PR-JAW","PR-JBE","PR-JBI","PR-JBK","PR-JBO","PR-JBP","PR-JBQ","PR-JBU","PR-JBX","PR-JHA","PR-JHC","PR-JHD","PR-JHE","PR-JHG","PR-JHH","PR-JHI","PR-JKC","PR-JKE","PR-JKJ","PR-JKK","PR-JKM","PR-LBA","PR-LCD","PR-LCH","PR-LCO","PR-LCP","PR-LCQ","PR-LCR","PR-LCT","PR-LCV","PR-LCZ","PR-LDC","PR-LDE","PR-LDG","PR-LDT","PR-LDV","PR-LDW","PR-LDZ","PR-MEO","PR-MEP","PR-MEX","PR-MEZ","PR-MLL","PR-MPN","PR-MPO","PR-MPY","PR-MPZ","PR-MRT","PR-NLN","PR-NSP","PR-OFC","PR-OFD","PR-OFE","PR-OFH","PR-OFJ","PR-OFK","PR-OFL","PR-OHA","PR-OHB","PR-OHC","PR-OHD","PR-OHE","PR-OHF","PR-OHG","PR-OHI","PR-OHJ","PR-OHK","PR-OHL","PR-OHN","PR-OHO","PR-OHP","PR-OHQ","PR-OHR","PR-OHS","PR-OHU","PR-OHV","PR-OHX","PR-OHY","PR-OHZ","PR-OMA","PR-OMB","PR-OMH","PR-OMK","PR-OMT","PR-OMY","PR-OOA","PR-OOB","PR-OOC","PR-OOG","PR-OOI","PR-OOL","PR-OOM","PR-OON","PR-OOP","PR-OOQ","PR-OOR","PR-OOS","PR-OOT","PR-OOU","PR-OOV","PR-OOW","PR-OOX","PR-OOY","PR-OTD","PR-OTF","PR-OTH","PR-OTI","PR-OTN","PR-OTP","PR-OTQ","PR-OTR","PR-OTS","PR-OTU","PR-OTW","PR-OTX","PR-OTY","PR-PDP","PR-PDS","PR-PDT","PR-PMS","PR-SEC","PR-SED","PR-SEE","PR-SEF","PR-SEO","PR-SES","PR-SET","PR-SEU","PR-SHL","PR-TESTE","PR-TTK","PR-WSG","PR-YXB","PR-YXT","PS-BTA","PS-BTB","PS-BTC","PS-BTD","PS-BTF","PS-BTJ","PS-BTK","PS-BTL","PS-BTO","PS-BTP","PS-BTW","PS-CDR","PS-CDT","PS-CDU","PS-CDV","PS-CDW","PS-CPU","PS-FCB","PS-GBN","PS-GBP","PS-LSC","PS-MSV","PT-GAD","PT-GAX","PT-MFE","PT-OCV","PT-SHO","TESTE"],"auditingType":["ACCI","RMNR","ACCD","Extra","ACC"],"contract":"","reportName":"","ata":null,"initialDateDoc":"2026-03-01","finalDateDoc":"2026-03-24T23:59:00Z","initialDatePub":null,"finalDatePub":null

}

GET all aircrafts:
https://api.rinaacc.com.br/aircraft/get-all?limit=100

*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"

*•	alt1: Y=80 rather than Y=30 
*•	alt2: d=0.025 rather than d=0.05 
*•	alt3: d=0.1 rather than d=0.05 
*•	alt4: harvest heuristic=max mean annual increment rather than Faustmann 
*•	alt5: genus/w/p = eucalypt/bioenergy/small rather than spatial
*•	alt6: genus/w/p = native broadleaf/solid wood/large rather than spatial
*•	alt7: geographic screen=brancalion rather than griscom
*•	alt8: geographic screen=bastin rather than griscom
*•	alt9: geographic screen=walker rather than griscom
*•	alt10: additionality=negative cost in addition to 
*•	alt11: Y=50 rather than Y=30  
*•	alt12: periodic clearing of natural regeneration
*•	alt13: suitability screen only (no buffer or additionality)
*•	alt14: suitability screen+buffer (no additionality)
*•	alt15: buffer+additionality (no screen)

*change the name of the frame so that I can use MAC curves in a separate frame later
frame rename default main


foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE { 

*remove BRB COK DJI MDV MHL NRU TKL TON TUV WSM

	
	use `ISO', clear

sum *
tab type
tab biome

gen BAUrefor=(bau_2020_2030*0.510928+bau_2030_2040*0.305911+bau_2040_2050*0.183161)
replace BAUrefor=.0571795 if BAUrefor==.

*Add sequential ID to sort back to original order, if needed
gen id=_n

*Data cleaning
replace griscom=0 if griscom==.
replace brancalion=0 if brancalion==.
replace bastin=0 if bastin==.
replace walker=0 if walker==.
replace nr_buffer=0 if nr_buffer==.
replace pl_buffer=0 if pl_buffer==.
	*drop deserts/xeric (biomes=13) and mangroves (biomes=14)
drop if biomes==13
drop if biomes==14
drop if nr_A==.
drop if type==.

*Implementation costs were given in 2011 USD; inflate to 2020 USD by multiplying by 1.1577
replace nr_cost=nr_cost*1.1577
replace ep_cost=ep_cost*1.1577
replace np_cost=np_cost*1.1577

*Plantation genus
gen genus=""
replace genus="neev" if type==1
replace genus="brev" if type==2
replace genus="brde" if type==3
replace genus="neev" if type==4
replace genus="cunn" if type==5
replace genus="euca" if type==6
replace genus="nede" if type==7
replace genus="neev" if type==8
replace genus="pinu" if type==9
replace genus="brde" if type==10
replace genus="neev" if type==11
replace genus="brde" if type==12
replace genus="brev" if type==13
replace genus="brde" if type==14
replace genus="neev" if type==15

gen genus_low="euca"
gen genus_high=""
replace genus_high="brev" if type==1
replace genus_high="brev" if type==2
replace genus_high="brde" if type==3
replace genus_high="brev" if type==4
replace genus_high="brev" if type==5
replace genus_high="brev" if type==6
replace genus_high="brde" if type==7
replace genus_high="brev" if type==8
replace genus_high="brev" if type==9
replace genus_high="brde" if type==10
replace genus_high="brev" if type==11
replace genus_high="brde" if type==12
replace genus_high="brev" if type==13
replace genus_high="brde" if type==14
replace genus_high="brev" if type==15

forvalues z=1/6 {
		gen genus_alt`z'=genus
		replace genus_alt`z'=genus_low if `z'==5
		replace genus_alt`z'=genus_high if `z'==6
}

	
	

*Rescale area from m^2 to ha
gen area=area_m2/10000
drop area_m2

*Root-shoot ratio based on IPCC 2019 V4 Ch4 Table 4.4 
sca ISO="`ISO'"
gen continent=""
	replace continent="AFRI" if ISO=="DZA" | ISO=="AGO" | ISO=="BEN" | ISO=="BWA" | ISO=="BFA" | ISO=="BDI" | ISO=="CPV" | ISO=="CMR" | ISO=="CAF" | ISO=="TCD" | ISO=="COM" | ISO=="COG" | ISO=="CIV" | ISO=="COD" | ISO=="DJI" | ISO=="EGY" | ISO=="GNQ" | ISO=="ERI" | ISO=="SWZ" | ISO=="ETH" | ISO=="GAB" | ISO=="GMB" | ISO=="GHA" | ISO=="GIN" | ISO=="GNB" | ISO=="KEN" | ISO=="LSO" | ISO=="LBR" | ISO=="LBY" | ISO=="MDG" | ISO=="MWI" | ISO=="MDV" | ISO=="MLI" | ISO=="MRT" | ISO=="MUS" | ISO=="MAR" | ISO=="MOZ" | ISO=="NAM" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="STP" | ISO=="SEN" | ISO=="SYC" | ISO=="SLE" | ISO=="SOM" | ISO=="ZAF" | ISO=="SSD" | ISO=="SDN" | ISO=="TZA" | ISO=="TGO" | ISO=="TUN" | ISO=="UGA" | ISO=="ESH" | ISO=="ZMB" | ISO=="ZWE" 
	
	replace continent="AMER" if ISO=="ATG" | ISO=="ARG" | ISO=="BRB" | ISO=="BLZ" | ISO=="BOL" | ISO=="BRA" | ISO=="CHL" | ISO=="COL" | ISO=="CRI" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="ECU" | ISO=="SLV" | ISO=="GUF" | ISO=="GRD" | ISO=="GTM" | ISO=="GUY" | ISO=="HTI" | ISO=="HND" | ISO=="JAM" | ISO=="MEX" | ISO=="NIC" | ISO=="PAN" | ISO=="PRY" | ISO=="PER" | ISO=="KNA" | ISO=="LCA" | ISO=="VCT" | ISO=="SUR" | ISO=="TTO" | ISO=="URY" | ISO=="VEN" 
	
	replace continent="ASIA" if ISO=="AFG" | ISO=="BGD" | ISO=="BTN" | ISO=="KHM" | ISO=="CHN" | ISO=="COK" | ISO=="PRK" | ISO=="FJI" | ISO=="IND" | ISO=="IDN" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KIR" | ISO=="KGZ" | ISO=="LAO" | ISO=="LBN" | ISO=="MYS" | ISO=="MHL" | ISO=="FSM" | ISO=="MNG" | ISO=="MMR" | ISO=="NRU" | ISO=="NPL" | ISO=="OMN" | ISO=="PAK" | ISO=="PLW" | ISO=="PSE" | ISO=="PNG" | ISO=="PHL" | ISO=="WSM" | ISO=="SLB" | ISO=="LKA" | ISO=="SYR" | ISO=="TJK" | ISO=="THA" | ISO=="TLS" | ISO=="TKL" | ISO=="TON" | ISO=="TKM" | ISO=="TUV" | ISO=="UZB" | ISO=="VUT" | ISO=="VNM" | ISO=="YEM" 

	replace continent="ASIA" if ISO=="ARM" | ISO=="AZE" | ISO=="GEO" | ISO=="TUR" 

forvalues z=1/6 { 
gen nr_rootshoot_alt`z'=0.26
	replace nr_rootshoot_alt`z'=0.825 if fao_ecoz==11 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.221 if fao_ecoz==11 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.207 if fao_ecoz==11 & continent=="ASIA"

	replace nr_rootshoot_alt`z'=0.232 if fao_ecoz==12 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.2845 if fao_ecoz==12 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.323 if fao_ecoz==12 & continent=="ASIA"
	
	replace nr_rootshoot_alt`z'=0.332 if fao_ecoz==13 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.334 if fao_ecoz==13 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.440 if fao_ecoz==13 & continent=="ASIA"
	
	*replace nr_rootshoot_alt`z'=??? if fao_ecoz==16 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.348 if fao_ecoz==16 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.322 if fao_ecoz==16 & continent=="ASIA"
	
	replace nr_rootshoot_alt`z'=0.232 if fao_ecoz==21 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.175 if fao_ecoz==21 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.230 if fao_ecoz==21 & continent=="ASIA"
		
	*replace nr_rootshoot_alt`z'=0.??? if fao_ecoz==22 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=0.336 if fao_ecoz==22 & continent=="AMER"
	replace nr_rootshoot_alt`z'=0.440 if fao_ecoz==22 & continent=="ASIA"
	
	*replace nr_rootshoot_alt`z'=0.??? if fao_ecoz==23 & continent=="AFRI"
	replace nr_rootshoot_alt`z'=1.338 if fao_ecoz==23 & continent=="AMER"
	replace nr_rootshoot_alt`z'=1.338 if fao_ecoz==23 & continent=="ASIA"
	 
	
	replace nr_rootshoot_alt`z'=0.466 if fao_ecoz==31 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace nr_rootshoot_alt`z'=0.337 if fao_ecoz==31 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace nr_rootshoot_alt`z'=0.225 if fao_ecoz==31 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace nr_rootshoot_alt`z'=0.243 if fao_ecoz==31 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	
	*replace nr_rootshoot_alt`z'=0.??? if fao_ecoz==32 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace nr_rootshoot_alt`z'=0.237 if fao_ecoz==32 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace nr_rootshoot_alt`z'=0.225 if fao_ecoz==32 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace nr_rootshoot_alt`z'=0.243 if fao_ecoz==32 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	
	
	*replace nr_rootshoot_alt`z'=0.??? if fao_ecoz==24, 25, 33, 34, 35, 41, 42, 43, 50, 90, 99 
	
gen pl_rootshoot_alt`z'=0.26
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==11 & continent=="AFRI"
	replace pl_rootshoot_alt`z'=0.170 if fao_ecoz==11 & continent=="AMER"
	replace pl_rootshoot_alt`z'=0.325 if fao_ecoz==11 & continent=="ASIA"

	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==12 & continent=="AFRI"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==12 & continent=="AMER"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==12 & continent=="ASIA"

	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==13 & continent=="AFRI"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==13 & continent=="AMER"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==13 & continent=="ASIA"
	
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==16 & continent=="AFRI"
	replace pl_rootshoot_alt`z'=2.158 if fao_ecoz==16 & continent=="AMER"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==16 & continent=="ASIA"	
	
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==21 & continent=="AFRI"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==21 & continent=="AMER"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==21 & continent=="ASIA"	
		
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==22 & continent=="AFRI"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==22 & continent=="AMER"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==22 & continent=="ASIA"	
		
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==23 & continent=="AFRI"
	*replace pl_rootshoot_alt`z'=??? if fao_ecoz==23 & continent=="AMER"
	replace pl_rootshoot_alt`z'=2.158 if fao_ecoz==23 & continent=="ASIA"
	
	
	*replace pl_rootshoot_alt`z'=0.??? if fao_ecoz==31 & continent=="AMER" & genus_alt`z'=="brde" | genus_alt`z'=="nede"
	replace pl_rootshoot_alt`z'=0.203 if fao_ecoz==31 & continent=="AMER" & genus_alt`z'=="pinu" | genus_alt`z'=="cunn" | genus_alt`z'=="brev" | genus_alt`z'=="neev"  
	replace pl_rootshoot_alt`z'=0.307 if fao_ecoz==31 & continent=="ASIA" & genus_alt`z'=="brde" | genus_alt`z'=="nede"
	replace pl_rootshoot_alt`z'=0.224 if fao_ecoz==31 & continent=="ASIA" & genus_alt`z'=="pinu" | genus_alt`z'=="cunn" | genus_alt`z'=="brev" | genus_alt`z'=="neev"  
	
	*replace pl_rootshoot_alt`z'=0.??? if fao_ecoz==32 & continent=="AMER" & genus_alt`z'=="brde" | genus_alt`z'=="nede"
	replace pl_rootshoot_alt`z'=0.237 if fao_ecoz==32 & continent=="AMER" & genus_alt`z'=="pinu" | genus_alt`z'=="cunn" | genus_alt`z'=="brev" | genus_alt`z'=="neev"  
	replace pl_rootshoot_alt`z'=0.307 if fao_ecoz==32 & continent=="ASIA" & genus_alt`z'=="brde" | genus_alt`z'=="nede"
	replace pl_rootshoot_alt`z'=0.224 if fao_ecoz==32 & continent=="ASIA" & genus_alt`z'=="pinu" | genus_alt`z'=="cunn" | genus_alt`z'=="brev" | genus_alt`z'=="neev"  
	}

*Truncate negative values of A and k at zero
replace nr_A=0 if nr_A<0 
replace nr_k=0 if nr_k<0

replace pinu_A=0 if pinu_A<0 
replace pinu_k=0 if pinu_k<0

replace cunn_A=0 if cunn_A<0 
replace cunn_k=0 if cunn_k<0

replace euca_A=0 if euca_A<0 
replace euca_k=0 if euca_k<0

replace brde_A=0 if brde_A<0 
replace brde_k=0 if brde_k<0

replace brev_A=0 if brev_A<0 
replace brev_k=0 if brev_k<0

replace nede_A=0 if nede_A<0 
replace nede_k=0 if nede_k<0

replace neev_A=0 if neev_A<0 
replace neev_k=0 if neev_k<0

*Set parameters (scalars)
	*time horizon (default=30)
	gen Y=30 
	forvalues z=1/6 {
		gen Y_alt`z'=Y
		replace Y_alt`z'=80 if `z'==1
	}
		
	*discount rate (default=0.05)
	gen d=0.05 
	forvalues z=1/6 {
		gen d_alt`z'=d
		replace d_alt`z'=0.025 if `z'==2
		replace d_alt`z'=0.1 if `z'==3
	}
	
	
	*set F(austmann)=0 for rotation length decision based on single harvest cycle; 
	*set F(austmann)=1 for rotation length decision based on infinite harvest cycle; (default)
	*set F(austmann)=2 for rotation length decision to maximize mean annual interval
	scalar F=1
	*annual carbon accumulation in soil
	scalar nrsoil=0.415107735
	scalar plantsoil=0.092749069
	*carbon pools to include in total carbon (totalC). set=1 to include, =0 to exclude. (default=1 for agbC, bgbC, soilC; =0 for harvestC)
	scalar agbC=1
	scalar bgbC=1
	scalar soilC=1
	scalar harvestC=1
	
*Fraction of aboveground carbon at time of harvest stored in long-lived wood products, w (default=0)
gen w=0
replace w=0.188 if ISO=="ATG" | ISO=="BLZ" | ISO=="BRB" | ISO=="CRI" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="GRD" | ISO=="GTM" | ISO=="HND" | ISO=="HTI" | ISO=="JAM" | ISO=="KNA" | ISO=="LCA" | ISO=="MEX" | ISO=="NIC" | ISO=="PAN" | ISO=="SLV" | ISO=="TTO" | ISO=="VCT"
replace w=0.268 if ISO=="ARG" | ISO=="BOL" | ISO=="BRA" | ISO=="CHL" | ISO=="COL" | ISO=="ECU" | ISO=="GUF" | ISO=="GUY" | ISO=="PER" | ISO=="PRY" | ISO=="SUR" | ISO=="URY" | ISO=="VEN"
replace w=0.355 if ISO=="AFG" | ISO=="ARM" | ISO=="AZE" | ISO=="BGD" | ISO=="BTN" | ISO=="CHN" | ISO=="GEO" | ISO=="IDN" | ISO=="IND" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KGZ" | ISO=="KHM" | ISO=="LAO" | ISO=="LBN" | ISO=="LKA" | ISO=="MMR" | ISO=="MNG" | ISO=="MYS" | ISO=="NPL" | ISO=="OMN" | ISO=="PAK" | ISO=="PHL" | ISO=="PNG" | ISO=="PRK" | ISO=="PSE" | ISO=="SYR" | ISO=="THA" | ISO=="TJK" | ISO=="TKM" | ISO=="TLS" | ISO=="TUR" | ISO=="UZB" | ISO=="VNM" | ISO=="YEM"
replace w=0.392 if ISO=="AGO" | ISO=="BDI" | ISO=="BEN" | ISO=="BFA" | ISO=="BWA" | ISO=="CAF" | ISO=="CIV" | ISO=="CMR" | ISO=="COD" | ISO=="COG" | ISO=="COM" | ISO=="CPV" | ISO=="DJI" | ISO=="DZA" | ISO=="EGY" | ISO=="ERI" | ISO=="ESH" | ISO=="ETH" | ISO=="GAB" | ISO=="GHA" | ISO=="GIN" | ISO=="GMB" | ISO=="GNB" | ISO=="GNQ" | ISO=="KEN" | ISO=="LBR" | ISO=="LBY" | ISO=="LSO" | ISO=="MAR" | ISO=="MDG" | ISO=="MDV" | ISO=="MLI" | ISO=="MOZ" | ISO=="MRT" | ISO=="MUS" | ISO=="MWI" | ISO=="NAM" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="SDN" | ISO=="SEN" | ISO=="SLE" | ISO=="SOM" | ISO=="SSD" | ISO=="STP" | ISO=="SWZ" | ISO=="SYC" | ISO=="TCD" | ISO=="TGO" | ISO=="TUN" | ISO=="TZA" | ISO=="UGA" | ISO=="ZAF" | ISO=="ZMB" | ISO=="ZWE"
replace w=0.415 if ISO=="COK" | ISO=="FJI" | ISO=="FSM" | ISO=="KIR" | ISO=="MHL" | ISO=="NRU" | ISO=="PLW" | ISO=="SLB" | ISO=="TKL" | ISO=="TON" | ISO=="TUV" | ISO=="VUT" | ISO=="WSM"

	forvalues z=1/6 {
		gen w_alt`z'=w
		replace w_alt`z'=0 if `z'==5
		replace w_alt`z'=0.595 if `z'==6
	}

*Revenue from wood products (net of harvest and delivery costs) as a scalar of aboveground carbon at time of harvest
gen p=0
replace p=52.65 if ISO=="ATG" | ISO=="BLZ" | ISO=="BRB" | ISO=="CRI" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="GRD" | ISO=="GTM" | ISO=="HND" | ISO=="HTI" | ISO=="JAM" | ISO=="KNA" | ISO=="LCA" | ISO=="NIC" | ISO=="PAN" | ISO=="SLV" | ISO=="TTO"| ISO=="VCT"
replace p=59.73 if ISO=="MEX"
replace p=61.04 if ISO=="BOL" | ISO=="BRA" | ISO=="COL" | ISO=="ECU" | ISO=="GUF" | ISO=="GUY" | ISO=="PER" | ISO=="SUR" | ISO=="VEN"
replace p=67.76 if ISO=="BGD" | ISO=="IDN" | ISO=="KHM" | ISO=="LAO" | ISO=="LKA" | ISO=="MMR" | ISO=="MYS" | ISO=="OMN" | ISO=="PHL" | ISO=="PNG" | ISO=="THA" | ISO=="TLS" | ISO=="VNM" | ISO=="YEM"
replace p=69.26 if ISO=="PRY"
replace p=71.24 if ISO=="AGO" | ISO=="BDI" | ISO=="BEN" | ISO=="BFA" | ISO=="CAF" | ISO=="CIV" | ISO=="CMR" | ISO=="COD" | ISO=="COG" | ISO=="COM" | ISO=="CPV" | ISO=="DJI" | ISO=="ERI" | ISO=="ETH" | ISO=="GAB" | ISO=="GHA" | ISO=="GIN" | ISO=="GMB" | ISO=="GNB" | ISO=="GNQ" | ISO=="KEN" | ISO=="LBR" | ISO=="MDG" | ISO=="MDV" | ISO=="MLI" | ISO=="MOZ" | ISO=="MRT" | ISO=="MUS" | ISO=="MWI" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="SDN" | ISO=="SEN" | ISO=="SLE" | ISO=="SOM" | ISO=="SSD" | ISO=="STP" | ISO=="SYC" | ISO=="TCD" | ISO=="TGO" | ISO=="TZA" | ISO=="UGA" | ISO=="ZMB" | ISO=="ZWE"
replace p=76.08 if ISO=="COK" | ISO=="FJI" | ISO=="FSM" | ISO=="KIR" | ISO=="MHL" | ISO=="NRU" | ISO=="PLW" | ISO=="SLB" | ISO=="TKL" | ISO=="TON" | ISO=="TUV" | ISO=="VUT" | ISO=="WSM"
replace p=76.88 if ISO=="IND"
replace p=80.003 if ISO=="ARG" | ISO=="CHL" | ISO=="URY"
replace p=80.83 if ISO=="BWA" | ISO=="NAM"
replace p=88.84 if ISO=="AFG" | ISO=="ARM" | ISO=="AZE" | ISO=="BTN" | ISO=="CHN" | ISO=="GEO" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KGZ" | ISO=="LBN" | ISO=="MNG" | ISO=="NPL" | ISO=="PAK" | ISO=="PRK" | ISO=="PSE" | ISO=="SYR" | ISO=="TJK" | ISO=="TKM" | ISO=="TUR" | ISO=="UZB"
replace p=93.40 if ISO=="DZA" | ISO=="EGY" | ISO=="ESH" | ISO=="LBY" | ISO=="LSO" | ISO=="MAR" | ISO=="SWZ" | ISO=="TUN" | ISO=="ZAF"

gen p_low=0
replace p_low=5.22 if ISO=="ATG" | ISO=="BLZ" | ISO=="BRB" | ISO=="CRI" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="GRD" | ISO=="GTM" | ISO=="HND" | ISO=="HTI" | ISO=="JAM" | ISO=="KNA" | ISO=="LCA" | ISO=="NIC" | ISO=="PAN" | ISO=="SLV" | ISO=="TTO" | ISO=="VCT" | ISO=="BOL" | ISO=="BRA" | ISO=="COL" | ISO=="ECU" | ISO=="GUF" | ISO=="GUY" | ISO=="PER" | ISO=="SUR" | ISO=="VEN" | ISO=="BGD" | ISO=="IDN" | ISO=="KHM" | ISO=="LAO" | ISO=="LKA" | ISO=="MMR" | ISO=="MYS" | ISO=="OMN" | ISO=="PHL" | ISO=="PNG" | ISO=="THA" | ISO=="TLS" | ISO=="VNM" | ISO=="YEM" | ISO=="AGO" | ISO=="BDI" | ISO=="BEN" | ISO=="BFA" | ISO=="CAF" | ISO=="CIV" | ISO=="CMR" | ISO=="COD" | ISO=="COG" | ISO=="COM" | ISO=="CPV" | ISO=="DJI" | ISO=="ERI" | ISO=="ETH" | ISO=="GAB" | ISO=="GHA" | ISO=="GIN" | ISO=="GMB" | ISO=="GNB" | ISO=="GNQ" | ISO=="KEN" | ISO=="LBR" | ISO=="MDG" | ISO=="MDV" | ISO=="MLI" | ISO=="MOZ" | ISO=="MRT" | ISO=="MUS" | ISO=="MWI" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="SDN" | ISO=="SEN" | ISO=="SLE" | ISO=="SOM" | ISO=="SSD" | ISO=="STP" | ISO=="SYC" | ISO=="TCD" | ISO=="TGO" | ISO=="TZA" | ISO=="UGA" | ISO=="ZMB" | ISO=="ZWE" | ISO=="COK" | ISO=="FJI" | ISO=="FSM" | ISO=="KIR" | ISO=="MHL" | ISO=="NRU" | ISO=="PLW" | ISO=="SLB" | ISO=="TKL" | ISO=="TON" | ISO=="TUV" | ISO=="VUT" | ISO=="WSM"
replace p_low=5.92 if ISO=="MEX" | ISO=="PRY" | ISO=="IND" | ISO=="BWA" | ISO=="NAM" 
replace p_low=6.84 if ISO=="ARG" | ISO=="CHL" | ISO=="URY" | ISO=="AFG" | ISO=="ARM" | ISO=="AZE" | ISO=="BTN" | ISO=="CHN" | ISO=="GEO" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KGZ" | ISO=="LBN" | ISO=="MNG" | ISO=="NPL" | ISO=="PAK" | ISO=="PRK" | ISO=="PSE" | ISO=="SYR" | ISO=="TJK" | ISO=="TKM" | ISO=="TUR" | ISO=="UZB" | ISO=="DZA" | ISO=="EGY" | ISO=="ESH" | ISO=="LBY" | ISO=="LSO" | ISO=="MAR" | ISO=="SWZ" | ISO=="TUN" | ISO=="ZAF"

gen p_high=0
replace p_high=49.6 if ISO=="ATG" | ISO=="BLZ" | ISO=="BRB" | ISO=="CRI" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="GRD" | ISO=="GTM" | ISO=="HND" | ISO=="HTI" | ISO=="JAM" | ISO=="KNA" | ISO=="LCA" | ISO=="NIC" | ISO=="PAN" | ISO=="SLV" | ISO=="TTO" | ISO=="VCT" | ISO=="BOL" | ISO=="BRA" | ISO=="COL" | ISO=="ECU" | ISO=="GUF" | ISO=="GUY" | ISO=="PER" | ISO=="SUR" | ISO=="VEN" | ISO=="BGD" | ISO=="IDN" | ISO=="KHM" | ISO=="LAO" | ISO=="LKA" | ISO=="MMR" | ISO=="MYS" | ISO=="OMN" | ISO=="PHL" | ISO=="PNG" | ISO=="THA" | ISO=="TLS" | ISO=="VNM" | ISO=="YEM" | ISO=="AGO" | ISO=="BDI" | ISO=="BEN" | ISO=="BFA" | ISO=="CAF" | ISO=="CIV" | ISO=="CMR" | ISO=="COD" | ISO=="COG" | ISO=="COM" | ISO=="CPV" | ISO=="DJI" | ISO=="ERI" | ISO=="ETH" | ISO=="GAB" | ISO=="GHA" | ISO=="GIN" | ISO=="GMB" | ISO=="GNB" | ISO=="GNQ" | ISO=="KEN" | ISO=="LBR" | ISO=="MDG" | ISO=="MDV" | ISO=="MLI" | ISO=="MOZ" | ISO=="MRT" | ISO=="MUS" | ISO=="MWI" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="SDN" | ISO=="SEN" | ISO=="SLE" | ISO=="SOM" | ISO=="SSD" | ISO=="STP" | ISO=="SYC" | ISO=="TCD" | ISO=="TGO" | ISO=="TZA" | ISO=="UGA" | ISO=="ZMB" | ISO=="ZWE" | ISO=="COK" | ISO=="FJI" | ISO=="FSM" | ISO=="KIR" | ISO=="MHL" | ISO=="NRU" | ISO=="PLW" | ISO=="SLB" | ISO=="TKL" | ISO=="TON" | ISO=="TUV" | ISO=="VUT" | ISO=="WSM"
replace p_high=56.27 if ISO=="MEX" | ISO=="PRY" | ISO=="IND" | ISO=="BWA" | ISO=="NAM" 
replace p_high=65.03 if ISO=="ARG" | ISO=="CHL" | ISO=="URY" | ISO=="AFG" | ISO=="ARM" | ISO=="AZE" | ISO=="BTN" | ISO=="CHN" | ISO=="GEO" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KGZ" | ISO=="LBN" | ISO=="MNG" | ISO=="NPL" | ISO=="PAK" | ISO=="PRK" | ISO=="PSE" | ISO=="SYR" | ISO=="TJK" | ISO=="TKM" | ISO=="TUR" | ISO=="UZB" | ISO=="DZA" | ISO=="EGY" | ISO=="ESH" | ISO=="LBY" | ISO=="LSO" | ISO=="MAR" | ISO=="SWZ" | ISO=="TUN" | ISO=="ZAF"

 
	forvalues z=1/6 {
		gen p_alt`z'=p
		replace p_alt`z'=p_low if `z'==5
		replace p_alt`z'=p_high if `z'==6
	}
	

*generate local to use in many functions involving {pinu cunn euca brde brev nede neev}
local genuslocal pinu cunn euca brde brev nede neev
	

*Discounted present value of aboveground carbon accumulation at discount rate=d (natural regeneration, no harvest)
*•	alt1: Y=80 rather than Y=30 
*•	alt2 d=0.025 rather than d=0.05 
*•	alt3 d=0.1 rather than d=0.05 
*•	alt4 harvest heuristic=max mean annual increment rather than Faustmann 

gen nr_accum=0
forvalues i=1/`=Y' {
    replace nr_accum=nr_accum + (1-d)^(`i'-1) * nr_A*((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)
}
*Calculate harvest year
foreach genu in `genuslocal' {
	gen `genu'_harvestyear=Y+1
}
forvalues i=2/`=Y' {
	foreach genu in `genuslocal' {
		gen `genu'_growth`i'= ((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)/(1-exp(-`genu'_k*(`i'-1)))^2
	}
}
forvalues i=3/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>d & F==0
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>d/(1-(1+d)^-`i-1') & F==1
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>1/`i' & F==2
	}
}
drop *growth*
*Discounted present value of carbon accumulation in standing stock at discount rate=d (plantation with harvest)
foreach genu in `genuslocal' {
	gen `genu'_stock=0
}
forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_stock=`genu'_stock + (1-d)^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*mod(`i',`genu'_harvestyear)))^2-(1-exp(-`genu'_k*mod(`i'-1,`genu'_harvestyear)))^2)
	}
}


*•	alt1: Y=80 rather than Y=30 
gen nr_accum_alt1=0
forvalues i=1/`=Y_alt1' {
    replace nr_accum_alt1=nr_accum_alt1 + (1-d)^(`i'-1) * nr_A*((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)
}
*Calculate harvest year
foreach genu in `genuslocal' {
	gen `genu'_harvestyear_alt1=Y_alt1+1
}
forvalues i=2/`=Y_alt1' {
	foreach genu in `genuslocal' {
		gen `genu'_growth`i'= ((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)/(1-exp(-`genu'_k*(`i'-1)))^2
	}
}
forvalues i=3/`=Y_alt1' {
	foreach genu in `genuslocal' {
		replace `genu'_harvestyear_alt1=`i' if `genu'_growth`i-1'>d/(1-(1+d)^-`i-1') 
	}
}
drop *growth*
*Discounted present value of carbon accumulation in standing stock at discount rate=d (plantation with harvest)
foreach genu in `genuslocal' {
	gen `genu'_stock_alt1=0
}
forvalues i=1/`=Y_alt1' {
	foreach genu in `genuslocal' {
		replace `genu'_stock_alt1=`genu'_stock_alt1 + (1-d)^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*mod(`i',`genu'_harvestyear_alt1)))^2-(1-exp(-`genu'_k*mod(`i'-1,`genu'_harvestyear_alt1)))^2)
	}
}

*•	alt2 d=0.025 rather than d=0.05
*•	alt3 d=0.1 rather than d=0.05  
forvalues z=2/3{
gen nr_accum_alt`z'=0
forvalues i=1/`=Y' {
    replace nr_accum_alt`z'=nr_accum_alt`z' + (1-d_alt`z')^(`i'-1) * nr_A*((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)
}
*Calculate harvest year
foreach genu in `genuslocal' {
	gen `genu'_harvestyear_alt`z'=Y+1
}
forvalues i=2/`=Y' {
	foreach genu in `genuslocal' {
		gen `genu'_growth`i'= ((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)/(1-exp(-`genu'_k*(`i'-1)))^2
	}
}
forvalues i=3/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_harvestyear_alt`z'=`i' if `genu'_growth`i-1'>d_alt`z'/(1-(1+d_alt`z')^-`i-1') 
	}
}
drop *growth*
*Discounted present value of carbon accumulation in standing stock at discount rate=d (plantation with harvest)
foreach genu in `genuslocal' {
	gen `genu'_stock_alt`z'=0
}
forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_stock_alt`z'=`genu'_stock_alt`z' + (1-d_alt`z')^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*mod(`i',`genu'_harvestyear_alt`z')))^2-(1-exp(-`genu'_k*mod(`i'-1,`genu'_harvestyear_alt`z')))^2)
	}
}
}

*•	alt4 harvest heuristic=max mean annual increment rather than Faustmann 
gen nr_accum_alt4=0
forvalues i=1/`=Y' {
    replace nr_accum_alt4=nr_accum_alt4 + (1-d)^(`i'-1) * nr_A*((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)
}
*Calculate harvest year
foreach genu in `genuslocal' {
	gen `genu'_harvestyear_alt4=Y+1
}
forvalues i=2/`=Y' {
	foreach genu in `genuslocal' {
		gen `genu'_growth`i'= ((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)/(1-exp(-`genu'_k*(`i'-1)))^2
	}
}
forvalues i=3/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_harvestyear_alt4=`i' if `genu'_growth`i-1'>1/`i' 
	}
}
drop *growth*
*Discounted present value of carbon accumulation in standing stock at discount rate=d (plantation with harvest)
foreach genu in `genuslocal' {
	gen `genu'_stock_alt4=0
}
forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_stock_alt4=`genu'_stock_alt4 + (1-d)^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*mod(`i',`genu'_harvestyear_alt4)))^2-(1-exp(-`genu'_k*mod(`i'-1,`genu'_harvestyear_alt4)))^2)
	}
}

forvalues z=5/6 {
	gen nr_accum_alt`z'=nr_accum
	foreach genu in `genuslocal' {
		gen `genu'_harvestyear_alt`z'=`genu'_harvestyear
		gen `genu'_stock_alt`z'=`genu'_stock
	}
}
	


*% of plantations that are exotic (FAO FRA 2020, Table 24), for all except cunn (native to China only), euca (exotic everywhere)
gen exotic=0

replace exotic=.74 if ISO=="AGO" | ISO=="BWA" | ISO=="COM" | ISO=="DJI" | ISO=="ERI" | ISO=="SWZ" | ISO=="ETH" | ISO=="KEN" | ISO=="LSO" | ISO=="MDG" | ISO=="MWI" | ISO=="MDV" | ISO=="MUS" | ISO=="MOZ" | ISO=="NAM" | ISO=="SYC" | ISO=="SOM" | ISO=="ZAF" | ISO=="SSD" | ISO=="SDN" | ISO=="TZA" | ISO=="UGA" | ISO=="ZMB" | ISO=="ZWE" 
replace exotic=.50 if ISO=="DZA" | ISO=="EGY" | ISO=="LBY" | ISO=="MAR" | ISO=="TUN" | ISO=="ESH"  
replace exotic=.74 if ISO=="BEN" | ISO=="BFA" | ISO=="BDI" | ISO=="CPV" | ISO=="CMR" | ISO=="CAF" | ISO=="TCD" | ISO=="COG" | ISO=="CIV" | ISO=="COD" | ISO=="GNQ" | ISO=="GAB" | ISO=="GMB" | ISO=="GHA" | ISO=="GIN" | ISO=="GNB" | ISO=="LBR" | ISO=="MLI" | ISO=="MRT" | ISO=="NER" | ISO=="NGA" | ISO=="RWA" | ISO=="STP" | ISO=="SEN" | ISO=="SLE" | ISO=="TGO"  

replace exotic=.31 if ISO=="CHN" | ISO=="PRK" | ISO=="MNG" 
replace exotic=.40 if ISO=="BGD" | ISO=="BTN" | ISO=="KHM" | ISO=="IND" | ISO=="IDN" | ISO=="LAO" |  ISO=="MYS" | ISO=="MMR" | ISO=="NPL" | ISO=="PAK" | ISO=="PHL" | ISO=="LKA" | ISO=="THA" | ISO=="TLS" | ISO=="VNM" 
replace exotic=.05 if ISO=="AFG" | ISO=="IRN" | ISO=="IRQ" | ISO=="JOR" | ISO=="KAZ" | ISO=="KGZ" | ISO=="LBN" | ISO=="OMN" | ISO=="PSE" | ISO=="SYR" | ISO=="TJK" | ISO=="TKM" | ISO=="UZB" | ISO=="YEM" | ISO=="ARM" | ISO=="AZE" | ISO=="GEO" | ISO=="TUR" 
replace exotic=.78 if ISO=="COK" | ISO=="FJI" | ISO=="KIR" | ISO=="MHL" | ISO=="FSM" | ISO=="NRU" | ISO=="PLW" | ISO=="PNG" | ISO=="WSM" | ISO=="SLB" | ISO=="TKL" | ISO=="TON" | ISO=="TUV" | ISO=="VUT" 

replace exotic=.32 if ISO=="ATG" | ISO=="BRB" | ISO=="CUB" | ISO=="DMA" | ISO=="DOM" | ISO=="GRD" | ISO=="HTI" | ISO=="KNA" | ISO=="LCA" | ISO=="VCT" | ISO=="TTO" 
replace exotic=.18 if ISO=="BLZ" | ISO=="CRI" | ISO=="SLV" | ISO=="GTM" | ISO=="HND" | ISO=="JAM" |  ISO=="MEX" | ISO=="NIC" | ISO=="PAN" 
replace exotic=.97 if ISO=="ARG" | ISO=="BOL" | ISO=="BRA" | ISO=="CHL" | ISO=="COL" | ISO=="ECU" | ISO=="GUF" | ISO=="GUY" | ISO=="PRY" | ISO=="PER" | ISO=="SUR" | ISO=="URY" | ISO=="VEN" 

gen native=1-exotic

forvalues z=1/4 {
	gen exotic_alt`z'=exotic
	gen native_alt`z'=native
}
	gen exotic_alt5=1
	gen exotic_alt6=0
	gen native_alt5=0
	gen native_alt6=1


*Discounted present value of establishment costs 
forvalues z=1/6 {
gen nr_npv_estcost_alt`z'=nr_cost
gen pinu_npv_estcost_alt`z'=exotic_alt`z'*ep_cost+native_alt`z'*np_cost
gen cunn_npv_estcost_alt`z'=ep_cost
	replace cunn_npv_estcost_alt`z'=np_cost if ISO=="CHN"
gen euca_npv_estcost_alt`z'=ep_cost
gen brde_npv_estcost_alt`z'=exotic_alt`z'*ep_cost+native_alt`z'*np_cost
gen brev_npv_estcost_alt`z'=exotic_alt`z'*ep_cost+native_alt`z'*np_cost
gen nede_npv_estcost_alt`z'=exotic_alt`z'*ep_cost+native_alt`z'*np_cost
gen neev_npv_estcost_alt`z'=exotic_alt`z'*ep_cost+native_alt`z'*np_cost

forvalues i=1/`=Y_alt`z'' {
	foreach genu in `genuslocal' {
		replace `genu'_npv_estcost_alt`z'=`genu'_npv_estcost_alt`z' + (1-d)^(`i'-1) * `genu'_npv_estcost_alt`z' if mod(`i',`genu'_harvestyear_alt`z')==0
	}
}
}

*Discounted present value of opportunity costs 
gen crop_npv_oppcost=0
forvalues i=1/`=Y' {
	replace crop_npv_oppcost=crop_npv_oppcost+crop_va*((1-d)^(`i'-1))
}

forvalues z=1/6 {
	gen crop_npv_oppcost_alt`z'=crop_npv_oppcost
}

*Discounted present value of harvested carbon
forvalues z=1/6 {
	foreach genu in `genuslocal' {
	gen `genu'_harvested_alt`z'=0
}

forvalues i=1/`=Y_alt`z'' {
	foreach genu in `genuslocal' {
			replace `genu'_harvested_alt`z'=`genu'_harvested_alt`z' + (1-d_alt`z')^(`i'-1) * `genu'_A*(1-exp(-`genu'_k*`i'))^2 if mod(`i',`genu'_harvestyear_alt`z')==0
	}
}
}

*Discounted present value of belowground biomass carbon, w/o harvest

forvalues z=1/6 {
	gen nr_bgC_alt`z'=nr_accum_alt`z'*nr_rootshoot_alt`z'
}


*Discounted present value of belowground biomass carbon, w/ harvest
forvalues z=1/6 {
	foreach genu in `genuslocal' {
	gen `genu'_bgC_whrv_alt`z'=`genu'_stock_alt`z'*pl_rootshoot_alt`z'
}
}

*Discounted present value of soil carbon, w/o harvest
forvalues z=1/6 {
	gen nr_soilC_alt`z'=0

forvalues i=1/`=Y_alt`z'' {
	replace nr_soilC_alt`z'=nr_soilC_alt`z' + (1-d_alt`z')^(`i'-1) * nrsoil
}
}

*Discounted present value of soil carbon, w/harvest
forvalues z=1/6 {
foreach genu in `genuslocal' {
	gen `genu'_soilC_whrv_alt`z'=0
}

forvalues i=1/`=Y_alt`z'' {
	replace nr_soilC_alt`z'=nr_soilC_alt`z' + (1-d_alt`z')^(`i'-1) * nrsoil
	foreach genu in `genuslocal' {
		replace `genu'_soilC_whrv_alt`z'=`genu'_soilC_whrv_alt`z' + (1-d_alt`z')^(`i'-1) * plantsoil if `i'<`genu'_harvestyear_alt`z'
	}
}
}


*total carbon without harvest
forvalues z=1/6 {
	gen nr_wohrv_totalC_alt`z'=agbC*nr_accum_alt`z'+bgbC*nr_bgC_alt`z'+soilC*nr_soilC_alt`z'
}

*total carbon with harvest
forvalues z=1/6 {
	foreach genu in `genuslocal' {
	gen `genu'_whrv_totalC_alt`z'=agbC*`genu'_stock_alt`z'+bgbC*`genu'_bgC_whrv_alt`z'+soilC*`genu'_soilC_whrv_alt`z'+harvestC*w*`genu'_harvested_alt`z'
}
}	

*choose the most likely genus 
forvalues z=1/6 {
	gen pl_stock_alt`z'=.
	gen pl_bgC_whrv_alt`z'=.
	gen pl_soilC_whrv_alt`z'=.
	gen pl_whrv_totalC_alt`z'=.
	gen pl_npv_estcost_alt`z'=.
	gen pl_harvested_alt`z'=.
}

forvalues z=1/6 {
	foreach genu in `genuslocal' {
		replace pl_stock_alt`z'=`genu'_stock_alt`z' if genus_alt`z'=="`genu'"
		replace pl_bgC_whrv_alt`z'=`genu'_bgC_whrv_alt`z' if genus_alt`z'=="`genu'"
		replace pl_soilC_whrv_alt`z'=`genu'_soilC_whrv_alt`z' if genus_alt`z'=="`genu'"
		replace pl_whrv_totalC_alt`z'=`genu'_whrv_totalC_alt`z' if genus_alt`z'=="`genu'"
		replace pl_npv_estcost_alt`z'=`genu'_npv_estcost_alt`z' if genus_alt`z'=="`genu'"
		replace pl_harvested_alt`z'=`genu'_harvested_alt`z' if genus_alt`z'=="`genu'"	
	}
}


*cost effectiveness 
forvalues z=1/6 {
	gen nr_wohrv_costeff_alt`z'=(crop_npv_oppcost_alt`z'+nr_npv_estcost_alt`z')/(3.67*nr_wohrv_totalC_alt`z')
	gen pl_whrv_costeff_alt`z'=(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z')/(3.67*pl_whrv_totalC_alt`z')
}

drop pinu* cunn* euca* brde* brev* nede* neev*


*which refor type is more costeffective
forvalues z=1/6 {
	gen refortype_whrv_alt`z'="."
	replace refortype_whrv_alt`z'="P" if (3.67*(pl_whrv_totalC_alt`z'))/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') > (3.67*nr_wohrv_totalC_alt`z')/(crop_npv_oppcost_alt`z'+nr_npv_estcost_alt`z') 
	replace refortype_whrv_alt`z'="N" if (3.67*(pl_whrv_totalC_alt`z'))/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') < (3.67*nr_wohrv_totalC_alt`z')/(crop_npv_oppcost_alt`z'+nr_npv_estcost_alt`z') 
	replace refortype_whrv_alt`z'="P" if (3.67*(pl_whrv_totalC_alt`z'))/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') < 0
	*tab refortype_whrv

	gen refortype_whrv_bu_alt`z'="."
	replace refortype_whrv_bu_alt`z'="P" if (3.67*pl_whrv_totalC_alt`z'*pl_buffer)/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') > (3.67*nr_wohrv_totalC_alt`z'*nr_buffer)/(crop_npv_oppcost_alt`z'+nr_npv_estcost_alt`z')  
	replace refortype_whrv_bu_alt`z'="N" if (3.67*pl_whrv_totalC_alt`z'*pl_buffer)/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') < (3.67*nr_wohrv_totalC_alt`z'*nr_buffer)/(crop_npv_oppcost_alt`z'+nr_npv_estcost_alt`z') 
	replace refortype_whrv_bu_alt`z'="P" if (3.67*pl_whrv_totalC_alt`z'*pl_buffer)/(crop_npv_oppcost_alt`z'+pl_npv_estcost_alt`z'-p*pl_harvested_alt`z') < 0
	*tab refortype_whrv_bu
}


*map of relative cost-effectiveness  (unbuffered only)
forvalues z=1/6 {
	gen rel_whrv_costeff_alt`z'=log(nr_wohrv_costeff_alt`z'/pl_whrv_costeff_alt`z')
}

*generate minimums
forvalues z=1/6 {
	gen mi_whrv_totalC_alt`z'=0
	replace mi_whrv_totalC_alt`z'=pl_whrv_totalC_alt`z' if refortype_whrv_alt`z'=="P"
	replace mi_whrv_totalC_alt`z'=nr_wohrv_totalC_alt`z' if refortype_whrv_alt`z'=="N"

	gen mi_whrv_bu_totalC_alt`z'=0
	replace mi_whrv_bu_totalC_alt`z'=pl_whrv_totalC_alt`z' if refortype_whrv_bu_alt`z'=="P"
	replace mi_whrv_bu_totalC_alt`z'=nr_wohrv_totalC_alt`z' if refortype_whrv_bu_alt`z'=="N"

	gen mi_whrv_costeff_alt`z'=.
	replace mi_whrv_costeff_alt`z'=pl_whrv_costeff_alt`z' if refortype_whrv_alt`z'=="P"
	replace mi_whrv_costeff_alt`z'=nr_wohrv_costeff_alt`z' if refortype_whrv_alt`z'=="N"

	gen mi_whrv_bu_costeff_alt`z'=.
	replace mi_whrv_bu_costeff_alt`z'=pl_whrv_costeff_alt`z' if refortype_whrv_bu_alt`z'=="P"
	replace mi_whrv_bu_costeff_alt`z'=nr_wohrv_costeff_alt`z' if refortype_whrv_bu_alt`z'=="N"
}

*fractions where natural regeneration is more cost-effective than plantation 
gen suitable=0
replace suitable=1 if nr_buffer==1
replace suitable=1 if pl_buffer==1
forvalues z=1/6 {
	gen suitable_alt`z'=suitable*griscom
}
	
forvalues z=1/6 {
	gen fract_whrv_costeff_alt`z'=.
	replace fract_whrv_costeff_alt`z'=0 if nr_wohrv_costeff_alt`z'>pl_whrv_costeff_alt`z'
	replace fract_whrv_costeff_alt`z'=1 if nr_wohrv_costeff_alt`z'<pl_whrv_costeff_alt`z'
	sum fract_whrv_costeff_alt`z' if suitable_alt`z'==1
}


*MARGINAL ABATEMENT COST CURVES 

*Odd but necessary hack to ensure that the MAC curves code still runs for countries that have fewer than 100 observations remaining: add 100 blank rows
set obs `=_N + 100' 
		*Set up a new frame to put the MAC curves in
		frame create MACC
		frame change MACC
		*set obs 100
		*gen price=_n
			set obs 25
			gen price=(_n-5)*5
		frame change main
		

	*The C values before were per hectare; change values to per cell
	forvalues z=1/6 {
		replace nr_wohrv_totalC_alt`z'=nr_wohrv_totalC_alt`z'*area
		replace pl_whrv_totalC_alt`z'=pl_whrv_totalC_alt`z'*area
		replace mi_whrv_totalC_alt`z'=mi_whrv_totalC_alt`z'*area
		replace mi_whrv_bu_totalC_alt`z'=mi_whrv_bu_totalC_alt`z'*area
	}
	forvalues z=1/6 {
		gen nr_wohrv_sGr_alt`z'=nr_wohrv_totalC_alt`z'*griscom
		gen pl_whrv_sGr_alt`z'=pl_whrv_totalC_alt`z'*griscom
		gen mi_whrv_sGr_alt`z'=mi_whrv_totalC_alt`z'*griscom
	}
	forvalues z=1/6 {
		gen nr_wohrv_sGr_bu_alt`z'=nr_wohrv_sGr_alt`z'*nr_buffer
		gen pl_whrv_sGr_bu_alt`z'=pl_whrv_sGr_alt`z'*pl_buffer
		gen mi_whrv_sGr_bu_alt`z'=mi_whrv_bu_totalC_alt`z'*griscom
	}



	forvalues z=1/6 {
		gen nr_wohrv_sGr_bu_ad_alt`z'=nr_wohrv_sGr_bu_alt`z'*(1-BAUrefor)
		gen pl_whrv_sGr_bu_ad_alt`z'=pl_whrv_sGr_bu_alt`z'*(1-BAUrefor)
		gen mi_whrv_sGr_bu_ad_alt`z'=mi_whrv_sGr_bu_alt`z'*(1-BAUrefor)
	}
		

	*MAC - natural regeneration (screened) (buffered) (additional)
	forvalues z=1/6 {
		gen MAC_nr_wohrv_sGr_bu_ad_alt`z'=.
		sort nr_wohrv_costeff_alt`z'
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(nr_wohrv_sGr_bu_ad_alt`z') if nr_wohrv_costeff_alt`z'<=(`i'-3)*10
		replace MAC_nr_wohrv_sGr_bu_ad_alt`z'=temp in `i'
		drop temp
		}
			
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_nr_wohrv_sGr_bu_ad_alt`z', from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
	}
		
		frame change MACC
		twoway (line price MAC_nr_wohrv_sGr_bu_ad_alt1) (line price MAC_nr_wohrv_sGr_bu_ad_alt2) (line price MAC_nr_wohrv_sGr_bu_ad_alt3) (line price MAC_nr_wohrv_sGr_bu_ad_alt4) (line price MAC_nr_wohrv_sGr_bu_ad_alt5) (line price MAC_nr_wohrv_sGr_bu_ad_alt6), legend(label(1 "Alt 1") label(2 "Alt 2") label(3 "Alt 3") label(4 "Alt 4") label(5 "Alt 5") label(6 "Alt 6")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
		
		*MAC - plantation (w/ harvest) (screened) (buffered) (additional)
	forvalues z=1/6 {
		gen MAC_pl_whrv_sGr_bu_ad_alt`z'=.
		sort pl_whrv_costeff_alt`z'
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(pl_whrv_sGr_bu_ad_alt`z') if pl_whrv_costeff_alt`z'<=(`i'-3)*10
		replace MAC_pl_whrv_sGr_bu_ad_alt`z'=temp in `i'
		drop temp
		}
			
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_pl_whrv_sGr_bu_ad_alt`z', from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
	}
		
		frame change MACC
		twoway (line price MAC_pl_whrv_sGr_bu_ad_alt1) (line price MAC_pl_whrv_sGr_bu_ad_alt2) (line price MAC_pl_whrv_sGr_bu_ad_alt3) (line price MAC_pl_whrv_sGr_bu_ad_alt4) (line price MAC_pl_whrv_sGr_bu_ad_alt5) (line price MAC_pl_whrv_sGr_bu_ad_alt6), legend(label(1 "Alt 1") label(2 "Alt 2") label(3 "Alt 3") label(4 "Alt 4") label(5 "Alt 5") label(6 "Alt 6")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
		
			
	*MAC - more costeffective (w/ harvest) (screened) (buffered) (additional)
	forvalues z=1/6 {
		gen MAC_mi_whrv_sGr_bu_ad_alt`z'=.
		sort mi_whrv_bu_costeff_alt`z'
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(mi_whrv_sGr_bu_ad_alt`z') if mi_whrv_bu_costeff_alt`z'<=(`i'-3)*10
		replace MAC_mi_whrv_sGr_bu_ad_alt`z'=temp in `i'
		drop temp
		}
			
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_mi_whrv_sGr_bu_ad_alt`z', from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
	}
		
		frame change MACC
		twoway (line price MAC_mi_whrv_sGr_bu_ad_alt1) (line price MAC_mi_whrv_sGr_bu_ad_alt2) (line price MAC_mi_whrv_sGr_bu_ad_alt3) (line price MAC_mi_whrv_sGr_bu_ad_alt4) (line price MAC_mi_whrv_sGr_bu_ad_alt5) (line price MAC_mi_whrv_sGr_bu_ad_alt6), legend(label(1 "Alt 1") label(2 "Alt 2") label(3 "Alt 3") label(4 "Alt 4") label(5 "Alt 5") label(6 "Alt 6")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
	

		
	


*Save MAC curves

frame change MACC
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"
save SA_MACC_`ISO', replace
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"
frame change main
frame drop MACC

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"

keep x y BAUrefor nr_wohrv_costeff* pl_whrv_costeff* suitable_alt*

save SA_maps_`ISO', replace
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"
		
}		









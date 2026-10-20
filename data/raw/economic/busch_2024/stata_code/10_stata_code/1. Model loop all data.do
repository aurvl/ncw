*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"

*Abbreviations used in variable names
*pl=plantation
*nr=natural regeneration
*np=plantation (native species)
*ep=plantation (exotic species)
*mi=minimum (cost option between plantation and natural regeneration)
*wohrv=without harvest
*whrv0=with harvest, excl. wood product revenue
*whrv=with harvest, incl. wood product revenue
*w=fraction of carbon at time of harvest that remains stored in wood products (discounted flow)
*p=revenue from wood products as a scalar of carbon at time of harvest
*s=screen
*Gr=Griscom
*Br=Brancalion
*Ba=Bastin
*Wa=Walker
*bu=buffer
*ad=additional
*rel=relative (cost effectiveness)


*change the name of the frame so that I can use MAC curves in a separate frame later
frame rename default main

foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE { 
	

	
	use `ISO', clear

sum *
tab type
tab biome

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
	
gen nr_rootshoot=0.26
	replace nr_rootshoot=0.825 if fao_ecoz==11 & continent=="AFRI"
	replace nr_rootshoot=0.221 if fao_ecoz==11 & continent=="AMER"
	replace nr_rootshoot=0.207 if fao_ecoz==11 & continent=="ASIA"

	replace nr_rootshoot=0.232 if fao_ecoz==12 & continent=="AFRI"
	replace nr_rootshoot=0.2845 if fao_ecoz==12 & continent=="AMER"
	replace nr_rootshoot=0.323 if fao_ecoz==12 & continent=="ASIA"
	
	replace nr_rootshoot=0.332 if fao_ecoz==13 & continent=="AFRI"
	replace nr_rootshoot=0.334 if fao_ecoz==13 & continent=="AMER"
	replace nr_rootshoot=0.440 if fao_ecoz==13 & continent=="ASIA"
	
	*replace nr_rootshoot=??? if fao_ecoz==16 & continent=="AFRI"
	replace nr_rootshoot=0.348 if fao_ecoz==16 & continent=="AMER"
	replace nr_rootshoot=0.322 if fao_ecoz==16 & continent=="ASIA"
	
	replace nr_rootshoot=0.232 if fao_ecoz==21 & continent=="AFRI"
	replace nr_rootshoot=0.175 if fao_ecoz==21 & continent=="AMER"
	replace nr_rootshoot=0.230 if fao_ecoz==21 & continent=="ASIA"
		
	*replace nr_rootshoot=0.??? if fao_ecoz==22 & continent=="AFRI"
	replace nr_rootshoot=0.336 if fao_ecoz==22 & continent=="AMER"
	replace nr_rootshoot=0.440 if fao_ecoz==22 & continent=="ASIA"
	
	*replace nr_rootshoot=0.??? if fao_ecoz==23 & continent=="AFRI"
	replace nr_rootshoot=1.338 if fao_ecoz==23 & continent=="AMER"
	replace nr_rootshoot=1.338 if fao_ecoz==23 & continent=="ASIA"
	 
	replace nr_rootshoot=0.466 if fao_ecoz==31 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace nr_rootshoot=0.337 if fao_ecoz==31 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace nr_rootshoot=0.225 if fao_ecoz==31 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace nr_rootshoot=0.243 if fao_ecoz==31 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	
	*replace nr_rootshoot=0.??? if fao_ecoz==32 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace nr_rootshoot=0.237 if fao_ecoz==32 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace nr_rootshoot=0.225 if fao_ecoz==32 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace nr_rootshoot=0.243 if fao_ecoz==32 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	
	*replace nr_rootshoot=0.??? if fao_ecoz==24, 25, 33, 34, 35, 41, 42, 43, 50, 90, 99 
	
gen pl_rootshoot=0.26
	*replace pl_rootshoot=??? if fao_ecoz==11 & continent=="AFRI"
	replace pl_rootshoot=0.170 if fao_ecoz==11 & continent=="AMER"
	replace pl_rootshoot=0.325 if fao_ecoz==11 & continent=="ASIA"

	*replace pl_rootshoot=??? if fao_ecoz==12 & continent=="AFRI"
	*replace pl_rootshoot=??? if fao_ecoz==12 & continent=="AMER"
	*replace pl_rootshoot=??? if fao_ecoz==12 & continent=="ASIA"

	*replace pl_rootshoot=??? if fao_ecoz==13 & continent=="AFRI"
	*replace pl_rootshoot=??? if fao_ecoz==13 & continent=="AMER"
	*replace pl_rootshoot=??? if fao_ecoz==13 & continent=="ASIA"
	
	*replace pl_rootshoot=??? if fao_ecoz==16 & continent=="AFRI"
	replace pl_rootshoot=2.158 if fao_ecoz==16 & continent=="AMER"
	*replace pl_rootshoot=??? if fao_ecoz==16 & continent=="ASIA"	
	
	*replace pl_rootshoot=??? if fao_ecoz==21 & continent=="AFRI"
	*replace pl_rootshoot=??? if fao_ecoz==21 & continent=="AMER"
	*replace pl_rootshoot=??? if fao_ecoz==21 & continent=="ASIA"	
		
	*replace pl_rootshoot=??? if fao_ecoz==22 & continent=="AFRI"
	*replace pl_rootshoot=??? if fao_ecoz==22 & continent=="AMER"
	*replace pl_rootshoot=??? if fao_ecoz==22 & continent=="ASIA"	
		
	*replace pl_rootshoot=??? if fao_ecoz==23 & continent=="AFRI"
	*replace pl_rootshoot=??? if fao_ecoz==23 & continent=="AMER"
	replace pl_rootshoot=2.158 if fao_ecoz==23 & continent=="ASIA"
	
	*replace pl_rootshoot=0.??? if fao_ecoz==31 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace pl_rootshoot=0.203 if fao_ecoz==31 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace pl_rootshoot=0.307 if fao_ecoz==31 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace pl_rootshoot=0.224 if fao_ecoz==31 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	
	*replace pl_rootshoot=0.??? if fao_ecoz==32 & continent=="AMER" & genus=="brde" | genus=="nede"
	replace pl_rootshoot=0.237 if fao_ecoz==32 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	replace pl_rootshoot=0.307 if fao_ecoz==32 & continent=="ASIA" & genus=="brde" | genus=="nede"
	replace pl_rootshoot=0.224 if fao_ecoz==32 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"  
	

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
	scalar Y=30 
	*discount rate (default=0.05)
	scalar d=0.05 
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

	

*generate local to use in many functions involving {pinu cunn euca brde brev nede neev}
local genuslocal pinu cunn euca brde brev nede neev
	
*Chapman-Richards carbon accumulation in year 30 (no harvest)
gen nr_Y30_d0=nr_A*(1-exp(-nr_k*Y))^2
foreach genu in `genuslocal' {
	gen `genu'_Y30_d0=`genu'_A*(1-exp(-`genu'_k*Y))^2
}

*Discounted present value of aboveground carbon accumulation at discount rate=d (no harvest)
gen nr_accum=0
foreach genu in `genuslocal' {
	gen `genu'_accum=0
}

forvalues i=1/`=Y' {
    replace nr_accum=nr_accum + (1-d)^(`i'-1) * nr_A*((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)
	foreach genu in `genuslocal' {
	replace `genu'_accum=`genu'_accum + (1-d)^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)
	}
}

*sum nr* pinu* cunn* euca* brde* brev* nede* neev*

*Calculate harvest year
gen nr_harvestyear=Y+1
foreach genu in `genuslocal' {
	gen `genu'_harvestyear=Y+1
}

forvalues i=2/`=Y' {
	gen nr_growth`i'= ((1-exp(-nr_k*`i'))^2-(1-exp(-nr_k*(`i'-1)))^2)/(1-exp(-nr_k*(`i'-1)))^2
	foreach genu in `genuslocal' {
		gen `genu'_growth`i'= ((1-exp(-`genu'_k*`i'))^2-(1-exp(-`genu'_k*(`i'-1)))^2)/(1-exp(-`genu'_k*(`i'-1)))^2
	}
}

forvalues i=3/`=Y' {
	replace nr_harvestyear=`i' if nr_growth`i-1'>d & F==0
	replace nr_harvestyear=`i' if nr_growth`i-1'>d/(1-(1+d)^-`i-1') & F==1
	replace nr_harvestyear=`i' if nr_growth`i-1'>1/`i' & F==2
	foreach genu in `genuslocal' {
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>d & F==0
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>d/(1-(1+d)^-`i-1') & F==1
		replace `genu'_harvestyear=`i' if `genu'_growth`i-1'>1/`i' & F==2
	}
}

drop *growth*

tab nr_harvestyear 
foreach genu in `genuslocal' {
	tab `genu'_harvestyear
}


*Discounted present value of carbon accumulation in standing stock at discount rate=d (with harvest)

foreach genu in `genuslocal' {
	gen `genu'_stock=0
}

forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_stock=`genu'_stock + (1-d)^(`i'-1) * `genu'_A*((1-exp(-`genu'_k*mod(`i',`genu'_harvestyear)))^2-(1-exp(-`genu'_k*mod(`i'-1,`genu'_harvestyear)))^2)
	}
}

*heatplot euca_stock y x, xbins(200) ybins(200) cut(0(10)100) 

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

*Discounted present value of establishment costs 
gen nr_npv_estcost=nr_cost
gen pinu_npv_estcost=exotic*ep_cost+native*np_cost
gen cunn_npv_estcost=ep_cost
	replace cunn_npv_estcost=np_cost if ISO=="CHN"
gen euca_npv_estcost=ep_cost
gen brde_npv_estcost=exotic*ep_cost+native*np_cost
gen brev_npv_estcost=exotic*ep_cost+native*np_cost
gen nede_npv_estcost=exotic*ep_cost+native*np_cost
gen neev_npv_estcost=exotic*ep_cost+native*np_cost

forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
		replace `genu'_npv_estcost=`genu'_npv_estcost + (1-d)^(`i'-1) * `genu'_npv_estcost if mod(`i',`genu'_harvestyear)==0
	}
}

*Discounted present value of opportunity costs 
gen crop_npv_oppcost=0
forvalues i=1/`=Y' {
	replace crop_npv_oppcost=crop_npv_oppcost+crop_va*((1-d)^(`i'-1))
}


*Discounted present value of harvested carbon
foreach genu in `genuslocal' {
	gen `genu'_harvested=0
}

forvalues i=1/`=Y' {
	foreach genu in `genuslocal' {
			replace `genu'_harvested=`genu'_harvested + (1-d)^(`i'-1) * `genu'_A*(1-exp(-`genu'_k*`i'))^2 if mod(`i',`genu'_harvestyear)==0
	}
}

*Discounted present value of belowground biomass carbon, w/o harvest
gen nr_bgC=nr_accum*nr_rootshoot
foreach genu in `genuslocal' {
	gen `genu'_bgC_wohrv=`genu'_accum*pl_rootshoot
}

*Discounted present value of belowground biomass carbon, w/ harvest
foreach genu in `genuslocal' {
	gen `genu'_bgC_whrv=`genu'_stock*pl_rootshoot
}

*Discounted present value of soil carbon, w/o harvest
gen nr_soilC=0
foreach genu in `genuslocal' {
	gen `genu'_soilC_wohrv=0
}

forvalues i=1/`=Y' {
	replace nr_soilC=nr_soilC + (1-d)^(`i'-1) * nrsoil
	foreach genu in `genuslocal' {
		replace `genu'_soilC_wohrv=`genu'_soilC_wohrv + (1-d)^(`i'-1) * plantsoil 
	} 
}

*Discounted present value of soil carbon, w/harvest
foreach genu in `genuslocal' {
	gen `genu'_soilC_whrv=0
}

forvalues i=1/`=Y' {
	replace nr_soilC=nr_soilC + (1-d)^(`i'-1) * nrsoil
	foreach genu in `genuslocal' {
		replace `genu'_soilC_whrv=`genu'_soilC_whrv + (1-d)^(`i'-1) * plantsoil if `i'<`genu'_harvestyear
	}
}

*total carbon without harvest
gen nr_wohrv_totalC=agbC*nr_accum+bgbC*nr_bgC+soilC*nr_soilC
foreach genu in `genuslocal' {
	gen `genu'_wohrv_totalC=agbC*`genu'_accum+bgbC*`genu'_bgC_wohrv+soilC*`genu'_soilC_wohrv
}
	
*total carbon with harvest
foreach genu in `genuslocal' {
	gen `genu'_whrv0_totalC=agbC*`genu'_stock+bgbC*`genu'_bgC_whrv+soilC*`genu'_soilC_whrv+harvestC*w*`genu'_harvested
	gen `genu'_whrv_totalC=agbC*`genu'_stock+bgbC*`genu'_bgC_whrv+soilC*`genu'_soilC_whrv+harvestC*w*`genu'_harvested
}
	
*Calculate breakeven carbon storage % (w1) (includes carbon accumulation only, but not cost)
foreach genu in `genuslocal' {
	gen `genu'_breakw1_nr=(nr_wohrv_totalC-`genu'_whrv_totalC)/(`genu'_harvested)
	gen `genu'_breakw1_`genu'=(`genu'_wohrv_totalC-`genu'_whrv_totalC)/(`genu'_harvested)
}	
	
*Calculate breakeven carbon storage % (w2) (includes both carbon accumulation and cost) 
foreach genu in `genuslocal' {
	gen `genu'_breakw2_nr=(nr_wohrv_totalC*((crop_npv_oppcost+`genu'_npv_estcost)/(crop_npv_oppcost+nr_npv_estcost))-`genu'_whrv_totalC)/(`genu'_harvested)
	gen `genu'_breakw2_`genu'=(`genu'_wohrv_totalC*((crop_npv_oppcost+`genu'_npv_estcost)/(crop_npv_oppcost+`genu'_npv_estcost))-`genu'_whrv_totalC)/(`genu'_harvested)
}

*Calculate breakeven carbon storage % (w3) (includes both carbon accumulation and cost, less revenue from wood products) 
foreach genu in `genuslocal' {
	gen `genu'_breakw3_nr=(nr_wohrv_totalC*((crop_npv_oppcost+`genu'_npv_estcost-p*`genu'_harvested)/(crop_npv_oppcost+nr_npv_estcost))-`genu'_whrv_totalC)/(`genu'_harvested)
	gen `genu'_breakw3_`genu'=(`genu'_wohrv_totalC*((crop_npv_oppcost+`genu'_npv_estcost-p*`genu'_harvested)/(crop_npv_oppcost+`genu'_npv_estcost))-`genu'_whrv_totalC)/(`genu'_harvested)
}



*sum *breakw*
*sum *breakw*, d

* Calculate breakeven timber sale revenue (p) ($/tC harvested biomass) (includes both carbon accumulation and cost. Is dependent on w=carbon storage %) 

foreach genu in `genuslocal' {
	gen `genu'_breakp_nr=(crop_npv_oppcost+`genu'_npv_estcost/`genu'_harvested)-((crop_npv_oppcost+nr_npv_estcost)*`genu'_whrv_totalC/(`genu'_harvested*nr_wohrv_totalC))-w*((crop_npv_oppcost+nr_npv_estcost)/nr_wohrv_totalC)
	gen `genu'_breakp_`genu'=(crop_npv_oppcost+`genu'_npv_estcost/`genu'_harvested)-((crop_npv_oppcost+`genu'_npv_estcost)*`genu'_whrv_totalC/(`genu'_harvested*`genu'_wohrv_totalC))-w*((crop_npv_oppcost+`genu'_npv_estcost)/`genu'_wohrv_totalC)
}



*sum *breakp*
*sum *breakp*, d

*choose the most likely genus 

gen pl_wohrv_totalC=.
gen pl_stock=.
gen pl_bgC_whrv=.
gen pl_soilC_whrv=.
gen pl_whrv0_totalC=.
gen pl_whrv_totalC=.
gen pl_npv_estcost=.
gen pl_harvested=.
gen pl_breakw1_nr=.
gen pl_breakw2_nr=.
gen pl_breakw3_nr=.
gen pl_breakp_nr=.


foreach genu in `genuslocal' {
	replace pl_wohrv_totalC=`genu'_wohrv_totalC if genus=="`genu'"
	replace pl_stock=`genu'_stock if genus=="`genu'"
	replace pl_bgC_whrv=`genu'_bgC_whrv if genus=="`genu'"
	replace pl_soilC_whrv=`genu'_soilC_whrv if genus=="`genu'"
	replace pl_whrv0_totalC=`genu'_whrv0_totalC if genus=="`genu'"
	replace pl_whrv_totalC=`genu'_whrv_totalC if genus=="`genu'"
	replace pl_npv_estcost=`genu'_npv_estcost if genus=="`genu'"
	replace pl_harvested=`genu'_harvested if genus=="`genu'"
	replace pl_breakw1_nr=`genu'_breakw1_nr if genus=="`genu'"
	replace pl_breakw2_nr=`genu'_breakw2_nr if genus=="`genu'"
	replace pl_breakw3_nr=`genu'_breakw3_nr if genus=="`genu'"
	replace pl_breakp_nr=`genu'_breakp_nr if genus=="`genu'"
}

*cost effectiveness 
gen nr_wohrv_costeff=(crop_npv_oppcost+nr_npv_estcost)/(3.67*nr_wohrv_totalC)
gen pl_wohrv_costeff=(crop_npv_oppcost+pl_npv_estcost)/(3.67*pl_wohrv_totalC)
gen pl_whrv0_costeff=(crop_npv_oppcost+pl_npv_estcost)/(3.67*pl_whrv0_totalC)
gen pl_whrv_costeff=(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested)/(3.67*pl_whrv_totalC)


sum *costeff*

*which refor type is more costeffective
gen refortype_wohrv="."
replace refortype_wohrv="P" if (3.67*pl_wohrv_totalC)/(crop_npv_oppcost+pl_npv_estcost) > (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost)  
replace refortype_wohrv="N" if (3.67*pl_wohrv_totalC)/(crop_npv_oppcost+pl_npv_estcost) < (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost)  
tab refortype_wohrv

gen refortype_whrv0="."
replace refortype_whrv0="P" if (3.67*(pl_whrv0_totalC))/(crop_npv_oppcost+pl_npv_estcost) > (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost) 
replace refortype_whrv0="N" if (3.67*(pl_whrv0_totalC))/(crop_npv_oppcost+pl_npv_estcost) < (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost) 
tab refortype_whrv0

gen refortype_whrv="."
replace refortype_whrv="P" if (3.67*(pl_whrv_totalC))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) > (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost) 
replace refortype_whrv="N" if (3.67*(pl_whrv_totalC))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < (3.67*nr_wohrv_totalC)/(crop_npv_oppcost+nr_npv_estcost) 
replace refortype_whrv="P" if (3.67*(pl_whrv_totalC))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < 0
tab refortype_whrv

gen refortype_wohrv_bu="."
replace refortype_wohrv_bu="P" if (3.67*pl_wohrv_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost) > (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost)  
replace refortype_wohrv_bu="N" if (3.67*pl_wohrv_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost) < (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost)  
tab refortype_wohrv_bu

gen refortype_whrv0_bu="."
replace refortype_whrv0_bu="P" if (3.67*pl_whrv0_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost) > (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost)  
replace refortype_whrv0_bu="N" if (3.67*pl_whrv0_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost) < (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost)  
tab refortype_whrv0_bu

gen refortype_whrv_bu="."
replace refortype_whrv_bu="P" if (3.67*pl_whrv_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) > (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost)  
replace refortype_whrv_bu="N" if (3.67*pl_whrv_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < (3.67*nr_wohrv_totalC*nr_buffer)/(crop_npv_oppcost+nr_npv_estcost) 
replace refortype_whrv_bu="P" if (3.67*pl_whrv_totalC*pl_buffer)/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < 0
tab refortype_whrv_bu

*map of relative cost-effectiveness  (unbuffered only)
gen rel_wohrv_costeff=log(nr_wohrv_costeff/pl_wohrv_costeff)
gen rel_whrv0_costeff=log(nr_wohrv_costeff/pl_whrv0_costeff)
gen rel_whrv_costeff=log(nr_wohrv_costeff/pl_whrv_costeff)
*heatplot rel_wohrv_costeff y x, xbins(200) ybins(200)

*generate minimums

gen mi_wohrv_totalC=0
replace mi_wohrv_totalC=pl_wohrv_totalC if refortype_wohrv=="P"
replace mi_wohrv_totalC=nr_wohrv_totalC if refortype_wohrv=="N"

gen mi_whrv0_totalC=0
replace mi_whrv0_totalC=pl_whrv0_totalC if refortype_whrv0=="P"
replace mi_whrv0_totalC=nr_wohrv_totalC if refortype_whrv0=="N"

gen mi_whrv_totalC=0
replace mi_whrv_totalC=pl_whrv_totalC if refortype_whrv=="P"
replace mi_whrv_totalC=nr_wohrv_totalC if refortype_whrv=="N"

gen mi_wohrv_bu_totalC=0
replace mi_wohrv_bu_totalC=pl_wohrv_totalC if refortype_wohrv_bu=="P"
replace mi_wohrv_bu_totalC=nr_wohrv_totalC if refortype_wohrv_bu=="N"

gen mi_whrv0_bu_totalC=0
replace mi_whrv0_bu_totalC=pl_whrv0_totalC if refortype_whrv0_bu=="P"
replace mi_whrv0_bu_totalC=nr_wohrv_totalC if refortype_whrv0_bu=="N"

gen mi_whrv_bu_totalC=0
replace mi_whrv_bu_totalC=pl_whrv_totalC if refortype_whrv_bu=="P"
replace mi_whrv_bu_totalC=nr_wohrv_totalC if refortype_whrv_bu=="N"

gen mi_wohrv_costeff=.
replace mi_wohrv_costeff=pl_wohrv_costeff if refortype_wohrv=="P"
replace mi_wohrv_costeff=nr_wohrv_costeff if refortype_wohrv=="N"

gen mi_whrv0_costeff=.
replace mi_whrv0_costeff=pl_whrv0_costeff if refortype_whrv0=="P"
replace mi_whrv0_costeff=nr_wohrv_costeff if refortype_whrv0=="N"

gen mi_whrv_costeff=.
replace mi_whrv_costeff=pl_whrv_costeff if refortype_whrv=="P"
replace mi_whrv_costeff=nr_wohrv_costeff if refortype_whrv=="N"

gen mi_wohrv_bu_costeff=.
replace mi_wohrv_bu_costeff=pl_wohrv_costeff if refortype_wohrv_bu=="P"
replace mi_wohrv_bu_costeff=nr_wohrv_costeff if refortype_wohrv_bu=="N"

gen mi_whrv0_bu_costeff=.
replace mi_whrv0_bu_costeff=pl_whrv0_costeff if refortype_whrv0_bu=="P"
replace mi_whrv0_bu_costeff=nr_wohrv_costeff if refortype_whrv0_bu=="N"

gen mi_whrv_bu_costeff=.
replace mi_whrv_bu_costeff=pl_whrv_costeff if refortype_whrv_bu=="P"
replace mi_whrv_bu_costeff=nr_wohrv_costeff if refortype_whrv_bu=="N"

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
		replace nr_wohrv_totalC=nr_wohrv_totalC*area
		replace pl_wohrv_totalC=pl_wohrv_totalC*area
		replace pl_whrv0_totalC=pl_whrv0_totalC*area
		replace pl_whrv_totalC=pl_whrv_totalC*area
		replace mi_wohrv_totalC=mi_wohrv_totalC*area
		replace mi_whrv0_totalC=mi_whrv0_totalC*area
		replace mi_whrv_totalC=mi_whrv_totalC*area
		replace mi_wohrv_bu_totalC=mi_wohrv_bu_totalC*area
		replace mi_whrv0_bu_totalC=mi_whrv0_bu_totalC*area
		replace mi_whrv_bu_totalC=mi_whrv_bu_totalC*area
	
	*generate local to use in many functions involving {pinu cunn euca brde brev nede neev}
	local MAClocal nr_wohrv pl_wohrv pl_whrv0 pl_whrv mi_wohrv mi_whrv0 mi_whrv

	*MAC curves - unscreened
	foreach item in `MAClocal' {
		gen MAC_`item'=.
		sort `item'_costeff
		*gen price=_n 
		*forvalues i=1/100 {
		*egen temp=total(`item'_totalC) if `item'_costeff<=`i'
			gen price=(_n-5)*5
			forvalues i=1/25 {
			egen temp=total(`item'_totalC) if `item'_costeff<=(`i'-5)*5
		replace MAC_`item'=temp in `i'
		drop temp
		}
				
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_`item', from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id
	}	
		
		frame change MACC
		twoway (line price MAC_nr_wohrv) (line price MAC_pl_wohrv) (line price MAC_pl_whrv0) (line price MAC_pl_whrv) (line price MAC_mi_wohrv) (line price MAC_mi_whrv0) (line price MAC_mi_whrv), legend(label(1 "natural") label(2 "plantation-unharvested") label(3 "plantation-harvested (excl. wood product revenue)") label(4 "plantation-harvested (incl. wood product revenue)") label(5 "more cost-effective unharvested") label(6 "more cost-effective harvested (excl. wood product revenue)") label(7 "more cost-effective harvested (incl. wood product revenue)")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO') legend(size(*.5))
		frame change main
		
	*MAC curves - screened by Griscom/Brancalion/Bastin/Walker
	
	*screen MAC curve based on reforestation potential map (Griscom et al 2017)
	***gen nr_wohrv_sGr=nr_wohrv_totalC*griscom
	*gen pl_wohrv_sGr=pl_wohrv_totalC*griscom
	*gen pl_whrv0_sGr=pl_whrv0_totalC*griscom
	***gen pl_whrv_sGr=pl_whrv_totalC*griscom
	*gen mi_wohrv_sGr=mi_wohrv_totalC*griscom
	*gen mi_whrv0_sGr=mi_wohrv0_totalC*griscom
	gen mi_whrv_sGr=mi_whrv_totalC*griscom
	gen mi_whrv_sBr=mi_whrv_totalC*brancalion
	gen mi_whrv_sBa=mi_whrv_totalC*bastin
	gen mi_whrv_sWa=mi_whrv_totalC*walker
	
	local screenlocal Gr Br Ba Wa
	
	foreach item in `screenlocal' {
		gen MAC_mi_whrv_s`item'=.
		sort mi_whrv_costeff
		*gen price=_n 
		*forvalues i=1/100 {
		*egen temp=total(mi_whrv_s`item') if mi_whrv_costeff<=`i'
			gen price=(_n-5)*5 
			forvalues i=1/25 {
			egen temp=total(mi_whrv_s`item') if mi_whrv_costeff<=(`i'-5)*5
		replace MAC_mi_whrv_s`item'=temp in `i'
		drop temp
		}
				
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_mi_whrv_s`item', from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
	}
	
		frame change MACC
		twoway (line price MAC_mi_whrv_sGr) (line price MAC_mi_whrv_sBr) (line price MAC_mi_whrv_sBa) (line price MAC_mi_whrv_sWa), legend(label(1 "Griscom") label(2 "Brancalion (Tropics only)") label(3 "Bastin") label(4 "Walker")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main

	*MAC curves - screened, buffered
	gen mi_whrv_sGr_bu=mi_whrv_bu_totalC*griscom
	gen MAC_mi_whrv_sGr_bu=.
		sort mi_whrv_bu_costeff
		*gen price=_n 
		*forvalues i=1/100 {
		*egen temp=total(mi_whrv_sGr_bu) if mi_whrv_bu_costeff<=`i'
				gen price=(_n-5)*5  
				forvalues i=1/25 {
				egen temp=total(mi_whrv_sGr_bu) if mi_whrv_bu_costeff<=(`i'-5)*5
		replace MAC_mi_whrv_sGr_bu=temp in `i'
		drop temp
		}
				
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_mi_whrv_sGr_bu, from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
	
	*MAC curves - screened, buffered, additional
	*reduce MAC based on additionality, i.e. subtracts reforestation (as a % of a cell) that "would have happened anyway" under Busch et al 2019 business-as-usual projection
	*the coefficients of 0.510928, 0.305911, 0.183161 are to upweight near-term reforestation consistent with a discount rate of 5%
	*ideally, we'd multiply carbon accumulation in each year by BAU in that year, but this is a reasonable approximation 
		gen BAUrefor=(bau_2020_2030*0.510928+bau_2030_2040*0.305911+bau_2040_2050*0.183161)
	
	*Outside of tropics, replace BAU missing values with default value
		replace BAUrefor=.0571795 if BAUrefor==.

	*MAC - more costeffective (w/ harvest) (screened) (buffered) (additional)
		gen MAC_mi_whrv_sGr_bu_ad=.
		sort mi_whrv_bu_costeff
		gen mi_whrv_sGr_bu_ad=(1-BAUrefor)*mi_whrv_sGr_bu	
		*gen price=_n
		*forvalues i=1/100 {
		*egen temp=total(mi_whrv_sGr_bu_ad) if mi_whrv_bu_costeff<=`i'
				gen price=(_n-5)*5 
				forvalues i=1/25 {
				egen temp=total(mi_whrv_sGr_bu_ad) if mi_whrv_bu_costeff<=(`i'-5)*5
		replace MAC_mi_whrv_sGr_bu_ad=temp in `i'
		drop temp
		}
			
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_mi_whrv_sGr_bu_ad, from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id	
		
		frame change MACC
		twoway (line price MAC_mi_whrv) (line price MAC_mi_whrv_sGr) (line price MAC_mi_whrv_sGr_bu) (line price MAC_mi_whrv_sGr_bu_ad), legend(label(1 "Unscreened") label(2 "Screened (Griscom)") label(3 "Screened, Buffered") label(4 "Screened, Buffered, Additional")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
	
	*MAC - all seven curves (screened) (buffered) (additional)
		
	gen nr_wohrv_bu_costeff=nr_wohrv_costeff
	gen pl_wohrv_bu_costeff=pl_wohrv_costeff
	gen pl_whrv0_bu_costeff=pl_whrv0_costeff  
	gen pl_whrv_bu_costeff=pl_whrv_costeff 
	
	gen nr_wohrv_sGr_bu_ad=nr_wohrv_totalC*griscom*nr_buffer*(1-BAUrefor)
	gen pl_wohrv_sGr_bu_ad=pl_wohrv_totalC*griscom*pl_buffer*(1-BAUrefor)
	gen pl_whrv0_sGr_bu_ad=pl_whrv0_totalC*griscom*pl_buffer*(1-BAUrefor)
	gen pl_whrv_sGr_bu_ad=pl_whrv_totalC*griscom*pl_buffer*(1-BAUrefor)
	gen mi_wohrv_sGr_bu_ad=mi_wohrv_bu_totalC*griscom*(1-BAUrefor)
	gen mi_whrv0_sGr_bu_ad=mi_whrv0_bu_totalC*griscom*(1-BAUrefor)
	
	
		
	frame change MACC
	drop MAC_mi_whrv_sGr_bu_ad
	frame change main
		
	foreach item in `MAClocal' {
		gen MAC_`item'_sGr_bu_ad=.
		sort `item'_bu_costeff
		*gen price=_n 
		*forvalues i=1/100 {
		*egen temp=total(`item'_sGr_bu_ad) if `item'_bu_costeff<=`i'
			gen price=(_n-5)*5
			forvalues i=1/25 {
			egen temp=total(`item'_sGr_bu_ad) if `item'_bu_costeff<=(`i'-5)*5
		replace MAC_`item'_sGr_bu_ad=temp in `i'
		drop temp
		}
				
			frame change MACC
			frlink m:1 price, frame(main)
			frget MAC_`item'_sGr_bu_ad, from(main)
			drop main
			frame change main
		
		drop price
		drop MAC_*
		sort id
	}	
	
	drop nr_wohrv_bu_costeff
	drop pl_wohrv_bu_costeff
	drop pl_whrv0_bu_costeff
	drop pl_whrv_bu_costeff
	
			frame change MACC
		twoway (line price MAC_nr_wohrv_sGr_bu_ad) (line price MAC_pl_wohrv_sGr_bu_ad) (line price MAC_pl_whrv0_sGr_bu_ad) (line price MAC_pl_whrv_sGr_bu_ad) (line price MAC_mi_wohrv_sGr_bu_ad) (line price MAC_mi_whrv0_sGr_bu_ad) (line price MAC_mi_whrv_sGr_bu_ad), legend(label(1 "natural") label(2 "plantation-unharvested") label(3 "plantation-harvested (excl. wood product revenue)") label(4 "plantation-harvested (incl. wood product revenue)") label(5 "more cost-effective unharvested") label(6 "more cost-effective harvested (excl. wood product revenue)") label(7 "more cost-effective harvested (incl. wood product revenue)")) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO') legend(size(*.5))
		frame change main
		
	
	*MAC curves - disaggregated by biome (shown here for more costeffective w/harvest, screened, buffered, additional)
	sort mi_whrv_bu_costeff
	*gen price=_n
		gen price=(_n-5)*5
	forvalues j=1/12 {
		gen MAC_mi_whrv_sGr_bu_ad_b`j'=.
		gen mi_whrv_sGr_bu_ad_b`j'=mi_whrv_sGr_bu_ad
		replace mi_whrv_sGr_bu_ad_b`j'=0 if biomes!=`j'
		
			egen max`j'=max(mi_whrv_sGr_bu_ad_b`j')
			if max`j'==0 replace MAC_mi_whrv_sGr_bu_ad_b`j'=0
			else if max`j'>0 {		
				
				*forvalues i=1/100{
				*egen temp=total(mi_whrv_sGr_bu_ad_b`j') if mi_whrv_bu_costeff<=`i'
					forvalues i=1/25 {
					egen temp=total(mi_whrv_sGr_bu_ad_b`j') if mi_whrv_bu_costeff<=(`i'-5)*5
				
				replace MAC_mi_whrv_sGr_bu_ad_b`j'=temp in `i'
				drop temp
			}
			}
			drop max*
			
		frame change MACC
		frlink m:1 price, frame(main)
		frget MAC_mi_whrv_sGr_bu_ad_b`j', from(main)
		drop main
		frame change main
	}

	drop price
	drop MAC_*
	sort id

	frame change MACC
	twoway (line price MAC_mi_whrv_sGr_bu_ad_b1) (line price MAC_mi_whrv_sGr_bu_ad_b2) (line price MAC_mi_whrv_sGr_bu_ad_b3) (line price MAC_mi_whrv_sGr_bu_ad_b4) (line price MAC_mi_whrv_sGr_bu_ad_b5) (line price MAC_mi_whrv_sGr_bu_ad_b6) (line price MAC_mi_whrv_sGr_bu_ad_b7) (line price MAC_mi_whrv_sGr_bu_ad_b8) (line price MAC_mi_whrv_sGr_bu_ad_b9) (line price MAC_mi_whrv_sGr_bu_ad_b10) (line price MAC_mi_whrv_sGr_bu_ad_b11) (line price MAC_mi_whrv_sGr_bu_ad_b12) (line price MAC_mi_whrv_sGr_bu_ad), legend(label(1 "Tropical & Subtropical Moist Broadleaf Forests") label(2 "Tropical & Subtropical Dry Broadleaf Forests") label(3 "Tropical & Subtropical Coniferous Forests") label(4 "Temperate Broadleaf & Mixed Forests") label(5 "Temperate Conifer Forests") label(6 "Boreal Forests/Taiga") label(7 "Tropical & Subtropical Grasslands, Savannas & Shrublands") label(8 "Temperate Grasslands, Savannas & Shrublands") label(9 "Flooded Grasslands & Savannas") label(10 "Montane Grasslands & Shrublands") label(11 "Tundra") label(12 "Mediterranean Forests, Woodlands & Scrub") label(13 "Total") ) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO') legend(size(*.5))
	frame change main

	
	*Disaggregate MAC curve by reforestation type/genus (shown here for more costeffective w/harvest screened)
	sort mi_whrv_bu_costeff
	*gen price=_n
		gen price=(_n-5)*5
	gen Genus=.
		replace Genus=0 if refortype_whrv_bu=="N"
		replace Genus=1 if refortype_whrv_bu=="P" & type==1
		replace Genus=2 if refortype_whrv_bu=="P" & type==2
		replace Genus=3 if refortype_whrv_bu=="P" & type==3
		replace Genus=4 if refortype_whrv_bu=="P" & type==4		
		replace Genus=5 if refortype_whrv_bu=="P" & type==5
		replace Genus=6 if refortype_whrv_bu=="P" & type==6
		replace Genus=7 if refortype_whrv_bu=="P" & type==7
		replace Genus=8 if refortype_whrv_bu=="P" & type==8
		replace Genus=9 if refortype_whrv_bu=="P" & type==9
		replace Genus=10 if refortype_whrv_bu=="P" & type==10
		replace Genus=11 if refortype_whrv_bu=="P" & type==11
		replace Genus=12 if refortype_whrv_bu=="P" & type==12
		replace Genus=13 if refortype_whrv_bu=="P" & type==13
		replace Genus=14 if refortype_whrv_bu=="P" & type==14		
		replace Genus=15 if refortype_whrv_bu=="P" & type==15
	forvalues j=0/15{
		gen MAC_mi_whrv_sGr_bu_ad_t`j'=.
		gen mi_whrv_sGr_bu_ad_t`j'=mi_whrv_sGr_bu_ad
		replace mi_whrv_sGr_bu_ad_t`j'=0 if Genus!=`j'
		
			egen max`j'=max(mi_whrv_sGr_bu_ad_t`j')
			if max`j'==0 replace MAC_mi_whrv_sGr_bu_ad_t`j'=0
			else if max`j'>0 {		
					*forvalues i=1/100{
					*egen temp=total(mi_whrv_sGr_bu_ad_t`j') if mi_whrv_bu_costeff<=`i'
							forvalues i=1/25{
							egen temp=total(mi_whrv_sGr_bu_ad_t`j') if mi_whrv_bu_costeff<=(`i'-5)*5
					replace MAC_mi_whrv_sGr_bu_ad_t`j'=temp in `i'
					drop temp
				}
			}
			drop max*
			
		frame change MACC
		frlink m:1 price, frame(main)
		frget MAC_mi_whrv_sGr_bu_ad_t`j', from(main)
		drop main
		frame change main
	}
	

	drop price
	drop MAC_*
	sort id
	
	frame change MACC
	twoway (line price MAC_mi_whrv_sGr_bu_ad_t1) (line price MAC_mi_whrv_sGr_bu_ad_t2) (line price MAC_mi_whrv_sGr_bu_ad_t3) (line price MAC_mi_whrv_sGr_bu_ad_t4) (line price MAC_mi_whrv_sGr_bu_ad_t5) (line price MAC_mi_whrv_sGr_bu_ad_t6) (line price MAC_mi_whrv_sGr_bu_ad_t7) (line price MAC_mi_whrv_sGr_bu_ad_t8) (line price MAC_mi_whrv_sGr_bu_ad), legend(label(1 "Natural Regeneration") label(2 "Pinus") label(3 "Cunninghamia") label(4 "Eucalyptus") label(5 "Broadleaf Deciduous") label(6 "Broadleaf Evergreen") label(7 "Needleleaf Deciduous") label(8 "Needleleaf Evergreen") label(9 "Total") ) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
	frame change main
	
	
*Save MAC curves

frame change MACC
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\MACCs"
save MACC_`ISO', replace
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"
frame change main
frame drop MACC

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
drop *_A 
drop *_k
drop biomes
drop bau*
drop np_cost ep_cost
drop fao_ecoz
drop id
drop native exotic
drop continent
drop *_rootshoot
drop pinu* cunn* euca* brde* brev* nede* neev*
drop nr_Y30_d0
drop nr_harvestyear
drop *totalC
drop mi_wohrv*
drop mi_whrv_bu_costeff
drop refortype*
drop rel*
drop Genus
drop mi_whrv_s*

gen country="`ISO'"

save maps_`ISO', replace
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"
		
}		










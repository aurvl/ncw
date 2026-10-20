*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"

*load aggregated maps for 138 LMICs
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE {
	append using maps_`ISO'
	disp "next"
}

gen suitable=0
replace suitable=1 if nr_buffer==1
replace suitable=1 if pl_buffer==1
replace suitable=suitable*griscom

gen suitable_nr=0
replace suitable_nr=1 if nr_buffer==1
replace suitable_nr=suitable_nr*griscom

gen suitable_pl=0
replace suitable_pl=1 if pl_buffer==1
replace suitable_pl=suitable_pl*griscom

*[implementation costs of reforestation]
*sum nr_npv_estcost, d
sum nr_npv_estcost if suitable==1, d

*sum pl_npv_estcost, d
sum pl_npv_estcost if suitable==1, d

*[opportunity costs of reforestation ] 
*sum crop_npv_oppcost, d
sum crop_npv_oppcost if suitable==1, d

	*[is difference in abatement cost due to opportunity cost in different areas?]
	sum crop_npv_oppcost if suitable_nr==1, d
	sum crop_npv_oppcost if suitable_pl==1, d

*[most likely plantation genus]
*tab type
tab type if suitable_pl==1

*[carbon accumulation from natural reforestation ] 
*sum nr_accum, d
sum nr_accum if suitable_nr==1, d

gen nr_totalC=nr_accum+nr_bgC+nr_soilC
*sum nr_totalC, d
sum nr_totalC if suitable_nr==1, d

*[carbon accumulation from plantation reforestation] 
*sum pl_stock, d
sum pl_stock if suitable_pl==1, d

gen pl_totalC=pl_stock+pl_bgC+pl_soilC+w*pl_harvested
*sum pl_totalC, d
sum pl_totalC if suitable_pl==1, d

gen pl_harvC=w*pl_harvested
*sum pl_harvC, d
sum pl_harvC if suitable_pl==1, d

*[cost-effectiveness of reforestation] 
*sum nr_wohrv_costeff, d
sum nr_wohrv_costeff if suitable_nr==1, d

*sum pl_whrv_costeff, d
sum pl_whrv_costeff if suitable_pl==1, d

gen pl_profit=0
replace pl_profit=1 if pl_whrv_costeff<0
*sum pl_profit, d
sum pl_profit if suitable_pl==1, d

*sum mi_whrv_costeff, d
sum mi_whrv_costeff if suitable==1, d

*[relative cost-effectiveness] 
gen fract_whrv_costeff=.
replace fract_whrv_costeff=0 if nr_wohrv_costeff>pl_whrv_costeff
replace fract_whrv_costeff=1 if nr_wohrv_costeff<pl_whrv_costeff
replace fract_whrv_costeff=0 if nr_buffer==0 & pl_buffer==1
replace fract_whrv_costeff=1 if nr_buffer==1 & pl_buffer==0
*sum fract_whrv_costeff, d
sum fract_whrv_costeff if suitable==1, d	

	*replace fract_whrv_costeff=. if nr_buffer==1 & pl_buffer==0 & nr_accum==0
	*replace fract_whrv_costeff=. if nr_buffer==0 & pl_buffer==1 & pl_stock==0
	*sum fract_whrv_costeff if suitable==1, d	

sum fract_whrv_costeff if suitable==1 & nr_buffer==1 & pl_buffer==1, d
	
*[aggregate area, gross cost, revenue, net cost (below $50/tCO2)]

gen impcost=0
replace impcost=nr_npv_estcost if fract_whrv_costeff==1
replace impcost=pl_npv_estcost if fract_whrv_costeff==0

gen cost=impcost+ crop_npv_oppcost
sum cost if suitable==1 & mi_whrv_costeff<=50	
	sum cost if suitable==1 & mi_whrv_costeff<=20
	sum cost if suitable==1 & mi_whrv_costeff<=100
*total area=obs*100
*total gross cost=obs*mean

	sum impcost if suitable==1 & mi_whrv_costeff<=50
	*total implementation cost=obs*mean
	
	sum crop_npv_oppcost if suitable==1 & mi_whrv_costeff<=50
	*total opportunity cost=obs*mean

sum cost if suitable==1 & mi_whrv_costeff<=50 & fract_whrv_costeff==1
*total area of natural regen=obs*100

sum cost if suitable==1 & mi_whrv_costeff<=50 & fract_whrv_costeff==0
*total area of plantation=obs*100

sum cost if suitable==1 & mi_whrv_costeff<=0 & fract_whrv_costeff==0
*total area of BAU plantation=obs*100

	 sum x if suitable==1 & nr_buffer==1 & mi_whrv_costeff<=50
	 sum x if suitable==1 & pl_buffer==1 & mi_whrv_costeff<=50

gen revenue=p*pl_harvested	
sum revenue if suitable==1 & mi_whrv_costeff<=50
	sum revenue if suitable==1 & mi_whrv_costeff<=20
	sum revenue if suitable==1 & mi_whrv_costeff<=100
*total revenue=obs*mean
*total net cost=total gross cost-total revenue



*[relative cost-effectiveness fraction by country]
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE {
	tab country if country=="`ISO'"
	sum fract_whrv_costeff if suitable==1 & country=="`ISO'"
}
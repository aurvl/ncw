*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

*Append maps data for multiple countries
clear all
*All countries (~1 hour to load)
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE {
	append using maps_`ISO'
	disp "next"
}

*Figure 1. 
*a)	implementation cost of natural forest regeneration
heatplot nr_npv_estcost y x , ybins(500) xbins(500)
graph save "Graph" nr_npv_estcost, replace

*b)	implementation cost of plantation (including replanting)
heatplot pl_npv_estcost y x , ybins(500) xbins(500) cut(0(10000)60000)
graph save "Graph" pl_npv_estcost, replace

*c) opportunity cost 
heatplot crop_npv_oppcost y x , ybins(500) xbins(500)
graph save "Graph" crop_npv_oppcost, replace

*d) most likely plantation genus
gen genusnum=0
replace genusnum=1 if genus=="pinu"
replace genusnum=2 if genus=="cunn"
replace genusnum=3 if genus=="euca"
replace genusnum=4 if genus=="brde"
replace genusnum=5 if genus=="brev"
replace genusnum=6 if genus=="nede"
replace genusnum=7 if genus=="neev"
*heatplot genusnum y x , ybins(500) xbins(500) cut (0.5(1)7.5) 
*graph save "Graph" genus, replace
heatplot type y x, ybins(500) xbins(500) cut (0.5(1)15.5)
graph save "Graph" type, replace

*e) aboveground carbon accumulation (npv w/o harvest, 30 years, 5% discount rate) for natural forest regeneration 
gen nr_wohrv_totalC=nr_accum+nr_bgC+nr_soilC
heatplot nr_wohrv_totalC y x, ybins(500) xbins(500)
graph save "Graph" nr_wohrv_totalC, replace

	*not part of figure 1 - plantation w/harvest (carbon in forest)
	gen pl_whrv_forestC=pl_stock+pl_bgC_whrv+pl_soilC_whrv
	heatplot pl_whrv_forestC y x, ybins(500) xbins(500)
	graph save "Graph" pl_whrv_forestC, replace
	*not part of figure 1 - plantation w/harvest (carbon in products)
	gen pl_whrv_productC=w*pl_harvested
	heatplot pl_whrv_productC y x, ybins(500) xbins(500)
	graph save "Graph" pl_whrv_productC, replace

*f) plantation w/harvest (total carbon)
gen pl_whrv_totalC=pl_whrv_forestC+pl_whrv_productC
heatplot pl_whrv_totalC y x , ybins(500) xbins(500)
graph save "Graph" pl_whrv_totalC, replace

*Figure 2. 
*a)	cost-effectiveness of natural forest regeneration ($/tCO2)
heatplot nr_wohrv_costeff y x , ybins(500) xbins(500) cuts (0(10)100)
graph save "Graph" nr_wohrv_costeff, replace

	heatplot nr_wohrv_costeff y x if nr_buffer==1 & griscom==1, ybins(500) xbins(500) cuts (0(10)100)
	heatplot nr_wohrv_costeff y x if nr_buffer==1 , ybins(500) xbins(500) cuts (0(10)100)

*b)	cost-effectiveness of plantation ($/tCO2)
heatplot pl_whrv_costeff y x , ybins(500) xbins(500) cuts (0(10)100)
graph save "Graph" pl_whrv_costeff, replace

	heatplot pl_whrv_costeff y x if pl_buffer==1 & griscom==1, ybins(500) xbins(500) cuts (0(10)100)
	heatplot pl_whrv_costeff y x if pl_buffer==1 , ybins(500) xbins(500) cuts (0(10)100)

	*not part of figure 2 - Effectiveness (tC), plantations unharvested	
	gen pl_wohrv_totalC=(crop_npv_oppcost+pl_npv_estcost)/(3.67*pl_wohrv_costeff)
	gen rel_wohrv_eff=log(pl_wohrv_totalC/nr_wohrv_totalC)
	sum rel_wohrv_eff
	heatplot rel_wohrv_eff y x , ybins(500) xbins(500)  cut (-12(6)12)
	graph save "Graph" rel_wohrv_eff, replace
	*b)not part of figure 2 - Effectiveness (tC), plantations harvested
	gen rel_whrv_eff=log(pl_whrv_totalC/nr_wohrv_totalC)
	sum rel_whrv_eff
	heatplot rel_whrv_eff y x , ybins(500) xbins(500)  cut (-12(6)12)
	graph save "Graph" rel_whrv_eff, replace
	*c)not part of figure 2 - Cost-effectiveness (tCO2/$), plantations unharvested	
	gen rel_wohrv_costeff=log(nr_wohrv_costeff/pl_wohrv_costeff)
	sum rel_wohrv_costeff
	heatplot rel_wohrv_costeff y x , ybins(500) xbins(500)  cut (-12(6)12)
	graph save "Graph" rel_wohrv_costeff, replace
	*d)not part of figure 2 - Cost-effectiveness (tCO2/$), plantations harvested, excl. product revenue	
	gen rel_whrv0_costeff=log(nr_wohrv_costeff/pl_whrv0_costeff)
	sum rel_whrv0_costeff
	heatplot rel_whrv0_costeff y x , ybins(500) xbins(500)  cut (-12(6)12)
	graph save "Graph" rel_whrv0_costeff, replace
	
*c) relative cost-effectiveness (tCO2/$), plantations harvested, incl. product revenue
gen rel_whrv_costeff=log(nr_wohrv_costeff/pl_whrv_costeff)
sum rel_whrv_costeff
	replace rel_whrv_costeff=12 if rel_whrv_costeff>12
	replace rel_whrv_costeff=-12 if rel_whrv_costeff<-12
	replace rel_whrv_costeff=12 if pl_whrv_costeff<0
heatplot rel_whrv_costeff y x , ybins(500) xbins(500)  cut (-12(6)12)
graph save "Graph" rel_whrv_costeff, replace

	* relative cost-effectiveness, (tCO2/$), plantations harvested, incl. product revenue - Buffered and Screened
	gen rel_whrv_costeff_bu=rel_whrv_costeff
	replace rel_whrv_costeff_bu=12 if nr_buffer==0 & pl_buffer==1
	replace rel_whrv_costeff_bu=-12 if nr_buffer==1 & pl_buffer==0
	replace rel_whrv_costeff_bu=. if nr_buffer==0 & pl_buffer==0
	heatplot rel_whrv_costeff y x if griscom==1, ybins(500) xbins(500)  cut (-12(6)12)

gen either_buffer=0
replace either_buffer=1 if nr_buffer==1
replace either_buffer=1 if pl_buffer==1
	   
*Figure S4
	*a) hist nr_npv_estcost if nr_npv_estcost<300 (old manuscript)
		hist nr_npv_estcost if griscom==1 & nr_buffer==1 & nr_npv_estcost<300
	*b) hist pl_npv_estcost
		hist pl_npv_estcost if griscom==1 & pl_buffer==1 & pl_npv_estcost<30000
	*c) hist crop_npv_oppcost
		hist crop_npv_oppcost if griscom==1 & either_buffer==1 & crop_npv_oppcost<30000
	*d) hist nr_accum
		hist nr_accum if griscom==1 & nr_buffer==1 & nr_accum<150
	*e) hist pl_stock
		hist pl_stock if griscom==1 & pl_buffer==1 & pl_stock<80
	*f) hist pl_hwpC
	    gen pl_hwpC=pl_harvested*w 
	    hist pl_hwpC if griscom==1 & pl_buffer==1 & pl_hwpC<80
	
*Figure S5 for the paper generated by Jacob	
*Figure S5
	*a) hist nr_wohrv_costeff if griscom==1 & nr_buffer==1 & nr_wohrv_costeff<200
	*b) hist pl_whrv_costeff if griscom==1 & pl_buffer==1 & pl_whrv_costeff<1000
	*c) gen suitable=0
	   *replace suitable=1 if nr_buffer==1
	   *replace suitable=1 if pl_buffer==1
	   *hist rel_whrv_costeff if griscom==1 & suitable==1
	*d) hist rel_whrv_costeff if griscom==1 & nr_buffer==1 & pl_buffer==1

*--------
*DO NOT USE THE LINES OF CODE BELOW
*--------







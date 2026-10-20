*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

*Sensitivity analysis generate and display results for manuscript

*MAC curves - alternate results 13-15 for natural regeneration, plantation, most cost-effect combination, at $20, $50, $100

*Append country-level MAC curves to create total MAC curve

	*Rename the MACC variables to add country identifier (ONLY NEEDS TO BE DONE ONCE)
	cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"


	
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BTN BWA CAF CHL CHN CIV CMR COD COG COL COM CPV CRI CUB DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MEX MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKM TLS TTO TUN TUR TZA UGA URY UZB VCT VEN VNM VUT YEM ZAF ZMB ZWE { 
		
		use SA_MACC_1315_`ISO'
		forvalues z=13/15 {
			replace MAC_nr_wohrv_sGr_bu_ad_alt`z'=0 if MAC_nr_wohrv_sGr_bu_ad_alt`z'==.
			replace MAC_pl_whrv_sGr_bu_ad_alt`z'=0 if MAC_pl_whrv_sGr_bu_ad_alt`z'==.
			replace MAC_mi_whrv_sGr_bu_ad_alt`z'=0 if MAC_mi_whrv_sGr_bu_ad_alt`z'==.
			rename MAC_nr_wohrv_sGr_bu_ad_alt`z' MAC_nr_wohrv_sGr_bu_ad_alt`z'_`ISO'
			rename MAC_pl_whrv_sGr_bu_ad_alt`z' MAC_pl_whrv_sGr_bu_ad_alt`z'_`ISO'
			rename MAC_mi_whrv_sGr_bu_ad_alt`z' MAC_mi_whrv_sGr_bu_ad_alt`z'_`ISO'
		}
			save, replace
	}


*Start a new sheet
clear all

set maxvar 10000

*Acquire and merge the country-by-country MAC curves
*set obs 100
*gen price=_n
	set obs 25
	gen price=(_n-5)*5

	foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BTN BWA CAF CHL CHN CIV CMR COD COG COL COM CPV CRI CUB DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MEX MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKM TLS TTO TUN TUR TZA UGA URY UZB VCT VEN VNM VUT YEM ZAF ZMB ZWE { 
		merge m:1 price using SA_MACC_1315_`ISO'
		drop _merge
	}	
		

*Sum the country-by-country MAC curves to obtain total MAC curves
foreach x in MAC_nr_wohrv_sGr_bu_ad_alt MAC_pl_whrv_sGr_bu_ad_alt MAC_mi_whrv_sGr_bu_ad_alt {
	forvalues z=13/15 {
		gen `x'`z'_tot=0
		foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BTN BWA CAF CHL CHN CIV CMR COD COG COL COM CPV CRI CUB DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MEX MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKM TLS TTO TUN TUR TZA UGA URY UZB VCT VEN VNM VUT YEM ZAF ZMB ZWE { 
		replace `x'`z'_tot=`x'`z'_tot+`x'`z'_`ISO'
		}		
	}
		     
}

save SA_MACC_1315_total, replace


*Append maps data for multiple countries
clear all
*All countries (~1 hour to load?)
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BTN BWA CAF CHL CHN CIV CMR COD COG COL COM CPV CRI CUB DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MEX MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKM TLS TTO TUN TUR TZA UGA URY UZB VCT VEN VNM VUT YEM ZAF ZMB ZWE {
	append using SA_maps_1315_`ISO'
	disp "next"
}

forvalues z=13/15 {
	gen fract_whrv_costeff_alt`z'=.
	replace fract_whrv_costeff_alt`z'=0 if nr_wohrv_costeff_alt`z'>pl_whrv_costeff_alt`z'
	replace fract_whrv_costeff_alt`z'=1 if nr_wohrv_costeff_alt`z'<pl_whrv_costeff_alt`z'
	replace fract_whrv_costeff_alt`z'=0 if pl_whrv_costeff_alt`z'<0
	replace fract_whrv_costeff_alt`z'=0 if pl_buffer==1 & nr_buffer==0
	replace fract_whrv_costeff_alt`z'=1 if pl_buffer==0 & nr_buffer==1
	sum fract_whrv_costeff_alt`z' if suitable_alt`z'==1 , d

}




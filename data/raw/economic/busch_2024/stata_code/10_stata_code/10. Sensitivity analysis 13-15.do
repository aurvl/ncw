*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

*Sensitivity analysis 13-15
clear all

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
frame rename default main
frame create MACC
frame create maps

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

foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BTN BWA CAF CHL CHN CIV CMR COD COG COL COM CPV CRI CUB DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MEX MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKM TLS TTO TUN TUR TZA UGA URY UZB VCT VEN VNM VUT YEM ZAF ZMB ZWE { 

*remove BRB COK DJI MDV MHL NRU TKL TON TUV WSM
		use maps_`ISO', clear

		
*MARGINAL ABATEMENT COST CURVES 

*Odd but necessary hack to ensure that the MAC curves code still runs for countries that have fewer than 100 observations remaining: add 100 blank rows
set obs `=_N + 100' 

	*Set up a new frame to put the MAC curves in
		frame change MACC
			cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"
			use SA_MACC_`ISO'
		frame change main
		cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
		
		gen nr_wohrv_totalC=nr_accum+nr_bgC+nr_soilC
		gen pl_whrv_totalC=pl_stock+pl_bgC_whrv+pl_soilC_whrv+w*pl_harvested
		
	*The C values before were per hectare; change values to per cell
		replace nr_wohrv_totalC=nr_wohrv_totalC*area
		replace pl_whrv_totalC=pl_whrv_totalC*area
	*add buffer
		gen nr_wohrv_bu=nr_wohrv_totalC*nr_buffer
		gen pl_whrv_bu=pl_whrv_totalC*pl_buffer	
	*calculate minimum
		gen refortype_whrv_bu="."
			replace refortype_whrv_bu="P" if (3.67*(pl_whrv_bu))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) > (3.67*nr_wohrv_bu)/(crop_npv_oppcost+nr_npv_estcost)
			replace refortype_whrv_bu="N" if (3.67*(pl_whrv_bu))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < (3.67*nr_wohrv_bu)/(crop_npv_oppcost+nr_npv_estcost) 
			replace refortype_whrv_bu="P" if (3.67*(pl_whrv_bu))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < 0
		gen mi_whrv_bu=0	
			replace mi_whrv_bu=nr_wohrv_bu if refortype_whrv_bu=="N"
			replace mi_whrv_bu=pl_whrv_bu if refortype_whrv_bu=="P"


*Suitability only (alt13)
		gen nr_wohrv_sGr=nr_wohrv_totalC*griscom
		gen pl_whrv_sGr=pl_whrv_totalC*griscom	
		
		gen refortype_whrv_sGr="."
			replace refortype_whrv_sGr="P" if (3.67*(pl_whrv_sGr))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) > (3.67*nr_wohrv_sGr)/(crop_npv_oppcost+nr_npv_estcost)
			replace refortype_whrv_sGr="N" if (3.67*(pl_whrv_sGr))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < (3.67*nr_wohrv_sGr)/(crop_npv_oppcost+nr_npv_estcost) 
			replace refortype_whrv_sGr="P" if (3.67*(pl_whrv_sGr))/(crop_npv_oppcost+pl_npv_estcost-p*pl_harvested) < 0

		gen mi_whrv_sGr=.
		replace mi_whrv_sGr=nr_wohrv_sGr if refortype_whrv_sGr=="N"
		replace mi_whrv_sGr=pl_whrv_sGr if refortype_whrv_sGr=="P"

*Screen+buffer (alt14)
		gen nr_wohrv_sGr_bu=nr_wohrv_bu*griscom
		gen pl_whrv_sGr_bu= pl_whrv_bu*griscom
		gen mi_whrv_sGr_bu= mi_whrv_bu*griscom

*No screen (alt15)
		gen nr_wohrv_bu_ad=nr_wohrv_bu*(1-BAUrefor)
		gen pl_whrv_bu_ad=pl_whrv_bu*(1-BAUrefor)
		gen mi_whrv_bu_ad=mi_whrv_bu*(1-BAUrefor)
		
		
*fractions where natural regeneration is more cost-effective than plantation (*NEED TO SCREEN AND BUFFER)
gen suitable=0
	replace suitable=1 if nr_buffer==1
	replace suitable=1 if pl_buffer==1
gen suitable_alt13=suitable*griscom
gen suitable_alt14=suitable*griscom
gen suitable_alt15=suitable

	
forvalues z=13/15 {
	gen fract_whrv_costeff_alt`z'=.
	replace fract_whrv_costeff_alt`z'=0 if nr_wohrv_costeff>pl_whrv_costeff
	replace fract_whrv_costeff_alt`z'=1 if nr_wohrv_costeff<pl_whrv_costeff
	sum fract_whrv_costeff_alt`z' if suitable_alt`z'==1
}		

forvalues z=13/15 {
	gen nr_wohrv_costeff_alt`z'=nr_wohrv_costeff
	gen pl_whrv_costeff_alt`z'=pl_whrv_costeff	
}	
	
	
*rename the values to fit the standard MAC curves code below (even though sGr, bu, ad may not be present)	
rename nr_wohrv_sGr nr_wohrv_sGr_bu_ad_alt13
rename pl_whrv_sGr pl_whrv_sGr_bu_ad_alt13
rename mi_whrv_sGr mi_whrv_sGr_bu_ad_alt13

rename nr_wohrv_sGr_bu nr_wohrv_sGr_bu_ad_alt14
rename pl_whrv_sGr_bu pl_whrv_sGr_bu_ad_alt14
rename mi_whrv_sGr_bu mi_whrv_sGr_bu_ad_alt14

rename nr_wohrv_bu_ad nr_wohrv_sGr_bu_ad_alt15
rename pl_whrv_bu_ad pl_whrv_sGr_bu_ad_alt15
rename mi_whrv_bu_ad mi_whrv_sGr_bu_ad_alt15

	
*generate MAC curves

	*MAC - natural regeneration 
	forvalues z=13/15 {
		gen MAC_nr_wohrv_sGr_bu_ad_alt`z'=.
		sort nr_wohrv_costeff
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(nr_wohrv_sGr_bu_ad_alt`z') if nr_wohrv_costeff<=(`i'-3)*10
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
		sort pxl_id	
	}
		
		frame change MACC
		twoway (line price MAC_nr_wohrv_sGr_bu_ad_alt13) (line price MAC_nr_wohrv_sGr_bu_ad_alt14) (line price MAC_nr_wohrv_sGr_bu_ad_alt15) , legend(label(1 "Alt 13") label(2 "Alt 14") label(3 "Alt 15")  ) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
		
		*MAC - plantation (w/ harvest)
	forvalues z=13/15 {
		gen MAC_pl_whrv_sGr_bu_ad_alt`z'=.
		sort pl_whrv_costeff
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(pl_whrv_sGr_bu_ad_alt`z') if pl_whrv_costeff<=(`i'-3)*10
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
		sort pxl_id	
	}
		
		frame change MACC
		twoway (line price MAC_pl_whrv_sGr_bu_ad_alt13) (line price MAC_pl_whrv_sGr_bu_ad_alt14) (line price MAC_pl_whrv_sGr_bu_ad_alt15) , legend(label(1 "Alt 13") label(2 "Alt 14") label(3 "Alt 15")  ) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main
		
			
	*MAC - more costeffective (w/ harvest)
	forvalues z=13/15 {
		gen MAC_mi_whrv_sGr_bu_ad_alt`z'=.
		sort mi_whrv_costeff
				gen price=(_n-3)*10 
				forvalues i=1/13 {
				egen temp=total(mi_whrv_sGr_bu_ad_alt`z') if mi_whrv_costeff<=(`i'-3)*10
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
		sort pxl_id	
	}


		frame change MACC
		twoway (line price MAC_mi_whrv_sGr_bu_ad_alt13) (line price MAC_mi_whrv_sGr_bu_ad_alt14) (line price MAC_mi_whrv_sGr_bu_ad_alt15) , legend(label(1 "Alt 13") label(2 "Alt 14") label(3 "Alt 15") ) xtitle("tons") ytitle("price per ton") ylabel(-20(20)100) title(`ISO')
		frame change main

*add to SA_MACC
frame change MACC
	cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"
	save SA_MACC_1315_`ISO', replace
frame change main

*add to SA_maps
	cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\SA"
	drop if x==.
		frame change main
			keep x y BAUrefor nr_wohrv_costeff_alt13 pl_whrv_costeff_alt13 nr_wohrv_costeff_alt14 pl_whrv_costeff_alt14 nr_wohrv_costeff_alt15 pl_whrv_costeff_alt15 suitable_alt13 suitable_alt14 suitable_alt15 nr_buffer pl_buffer
			save SA_maps_1315_`ISO', replace
		frame change main
	cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"		
		
	}
	
		





*This is separate code to generate BAUrefor where it doesn't already exist
*--------
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"
frame rename default main
frame create maps
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE { 

use `ISO',clear
gen BAUrefor=(bau_2020_2030*0.510928+bau_2030_2040*0.305911+bau_2040_2050*0.183161)
replace BAUrefor=.0571795 if BAUrefor==.

frame change maps
		cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
		use maps_`ISO', clear
		frlink m:1 pxl_id, frame(main)
		frget BAUrefor, from(main)
		drop main
		save maps_`ISO', replace
frame change main
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\dtas"

}

*--------
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\maps"
foreach ISO in AFG AGO ARG ARM ATG AZE BDI BEN BFA BGD BLZ BOL BRA BRB BTN BWA CAF CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB DJI DMA DOM DZA ECU EGY ERI ESH ETH FJI FSM GAB GEO GHA GIN GMB GNB GNQ GRD GTM GUF GUY HND HTI IDN IND IRN IRQ JAM JOR KAZ KEN KGZ KHM KNA LAO LBN LBR LBY LCA LKA LSO MAR MDG MDV MEX MHL MLI MMR MNG MOZ MRT MUS MWI MYS NAM NER NGA NIC NPL NRU OMN PAK PAN PER PHL PLW PNG PRK PRY PSE RWA SDN SEN SLB SLE SLV SOM SSD STP SUR SWZ SYC SYR TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TZA UGA URY UZB VCT VEN VNM VUT WSM YEM ZAF ZMB ZWE { 
	use maps_`ISO', clear
	replace BAUrefor=.0571795 if BAUrefor==.
	save maps_`ISO', replace
}
*--------









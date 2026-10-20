*Stata code accompanying Busch, J., Bukoski, J.J., Cook-Patton, S.C., Griscom, B.,  Kaczan, D., Potts, M.D., Yi, Y., Vincent, J. (2024). "Tree planting vs. natural forest regeneration: relative cost-effectiveness at mitigating climate change." Nature Climate Change. 

*Code to append MAC curves for multiple countries

cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\MACCs"

*Rename the MACC variables to add country identifier (ONLY NEEDS TO BE DONE ONCE)


*foreach ISO in AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DZA EGY ERI ESH ETH GAB GHA GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE {
*foreach ISO in ARG ATG BLZ BOL BRA BRB CHL COL CRI CUB DMA DOM ECU GRD GTM GUF GUY HND HTI JAM LCA MEX NIC PAN PER PRY SLV SUR TTO URY VCT VEN {
*foreach ISO in AFG ARM AZE BGD BTN COK CHN FJI FSM GEO IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL TKM TLS TON TUR TUV UZB VUT VNM WSM YEM {



foreach ISO in AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE ARG ATG BLZ BOL BRA BRB CHL COL CRI CUB DMA DOM ECU GRD GTM GUF GUY HND HTI JAM KNA LCA MEX NIC PAN PER PRY SLV SUR TTO URY VCT VEN AFG ARM AZE BGD BTN COK CHN FJI FSM GEO IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL TKM TLS TON TUR TUV UZB VUT VNM WSM YEM {
	
	use MACC_`ISO'
	foreach x in MAC_nr_wohrv MAC_pl_wohrv MAC_pl_whrv0 MAC_pl_whrv MAC_mi_wohrv MAC_mi_whrv0 MAC_mi_whrv MAC_mi_whrv_sGr MAC_mi_whrv_sBr MAC_mi_whrv_sBa MAC_mi_whrv_sWa MAC_mi_whrv_sGr_bu MAC_nr_wohrv_sGr_bu_ad MAC_pl_wohrv_sGr_bu_ad MAC_pl_whrv0_sGr_bu_ad MAC_pl_whrv_sGr_bu_ad MAC_mi_wohrv_sGr_bu_ad MAC_mi_whrv0_sGr_bu_ad MAC_mi_whrv_sGr_bu_ad MAC_mi_whrv_sGr_bu_ad_b1 MAC_mi_whrv_sGr_bu_ad_b2 MAC_mi_whrv_sGr_bu_ad_b3 MAC_mi_whrv_sGr_bu_ad_b4 MAC_mi_whrv_sGr_bu_ad_b5 MAC_mi_whrv_sGr_bu_ad_b6 MAC_mi_whrv_sGr_bu_ad_b7 MAC_mi_whrv_sGr_bu_ad_b8 MAC_mi_whrv_sGr_bu_ad_b9 MAC_mi_whrv_sGr_bu_ad_b10 MAC_mi_whrv_sGr_bu_ad_b11 MAC_mi_whrv_sGr_bu_ad_b12 MAC_mi_whrv_sGr_bu_ad_t1 MAC_mi_whrv_sGr_bu_ad_t2 MAC_mi_whrv_sGr_bu_ad_t3 MAC_mi_whrv_sGr_bu_ad_t4 MAC_mi_whrv_sGr_bu_ad_t5 MAC_mi_whrv_sGr_bu_ad_t6 MAC_mi_whrv_sGr_bu_ad_t7 MAC_mi_whrv_sGr_bu_ad_t8  {
		replace `x'=0 if `x'==.
		rename `x' `x'_`ISO'
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


foreach ISO in AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE ARG ATG BLZ BOL BRA BRB CHL COL CRI CUB DMA DOM ECU GRD GTM GUF GUY HND HTI JAM KNA LCA MEX NIC PAN PER PRY SLV SUR TTO URY VCT VEN AFG BGD BTN COK CHN FJI FSM IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL TKM TLS TON TUV UZB VUT VNM WSM YEM ARM AZE GEO TUR {
	merge m:1 price using MACC_`ISO'
	drop _merge
}




*Sum the country-by-country MAC curves to obtain total MAC curves
foreach x in MAC_nr_wohrv_ MAC_pl_wohrv_ MAC_pl_whrv0_ MAC_pl_whrv_ MAC_mi_wohrv_ MAC_mi_whrv0_ MAC_mi_whrv_ MAC_mi_whrv_sGr_ MAC_mi_whrv_sBr_ MAC_mi_whrv_sBa_ MAC_mi_whrv_sWa_  MAC_mi_whrv_sGr_bu_ MAC_nr_wohrv_sGr_bu_ad_ MAC_pl_wohrv_sGr_bu_ad_ MAC_pl_whrv0_sGr_bu_ad_ MAC_pl_whrv_sGr_bu_ad_ MAC_mi_wohrv_sGr_bu_ad_ MAC_mi_whrv0_sGr_bu_ad_  MAC_mi_whrv_sGr_bu_ad_ MAC_mi_whrv_sGr_bu_ad_b1_ MAC_mi_whrv_sGr_bu_ad_b2_ MAC_mi_whrv_sGr_bu_ad_b3_ MAC_mi_whrv_sGr_bu_ad_b4_ MAC_mi_whrv_sGr_bu_ad_b5_ MAC_mi_whrv_sGr_bu_ad_b6_ MAC_mi_whrv_sGr_bu_ad_b7_ MAC_mi_whrv_sGr_bu_ad_b8_ MAC_mi_whrv_sGr_bu_ad_b9_ MAC_mi_whrv_sGr_bu_ad_b10_ MAC_mi_whrv_sGr_bu_ad_b11_ MAC_mi_whrv_sGr_bu_ad_b12_ MAC_mi_whrv_sGr_bu_ad_t1_ MAC_mi_whrv_sGr_bu_ad_t2_ MAC_mi_whrv_sGr_bu_ad_t3_ MAC_mi_whrv_sGr_bu_ad_t4_ MAC_mi_whrv_sGr_bu_ad_t5_ MAC_mi_whrv_sGr_bu_ad_t6_ MAC_mi_whrv_sGr_bu_ad_t7_ MAC_mi_whrv_sGr_bu_ad_t8_ {
	
	gen `x'AMER=0
	foreach ISO in ARG BLZ BOL BRA BRB CHL COL CRI ECU GTM GUF GUY HND KNA MEX NIC PAN PER PRY SLV SUR URY VEN ATG CUB DMA DOM GRD HTI JAM LCA VCT TTO {
		replace `x'AMER=`x'AMER+`x'`ISO'
	}
	
	gen `x'AFRI=0
	foreach ISO in AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE {
		replace `x'AFRI=`x'AFRI+`x'`ISO'
	}	
	
	gen `x'ASIA=0
	foreach ISO in AFG BGD BTN COK CHN FJI FSM IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL TKM TLS TON TUV UZB VUT VNM WSM YEM ARM AZE GEO TUR {
		replace `x'ASIA=`x'ASIA+`x'`ISO'
	}		
	
	
	gen `x'total=0
	foreach ISO in ARG BLZ BOL BRA BRB CHL COL CRI ECU GTM GUF GUY HND KNA MEX NIC PAN PER PRY SLV SUR URY VEN ATG CUB DMA DOM GRD HTI JAM LCA VCT TTO AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE AFG BGD BTN COK CHN FJI FSM IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL TKM TLS TON TUV UZB VUT VNM WSM YEM ARM AZE GEO TUR {
		replace `x'total=`x'total+`x'`ISO'
	}		
	
		     
}

save MACC_total, replace


*Graph the MAC curves

twoway (line price MAC_nr_wohrv_sGr_bu_ad_total) (line price MAC_pl_whrv_sGr_bu_ad_total) (line price MAC_mi_whrv_sGr_bu_ad_total) , legend(label(1 "Natural regeneration") label(2 "Plantation with harvest") label(3 "More cost-effective")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))



twoway (line price MAC_nr_wohrv_total) (line price MAC_pl_wohrv_total) (line price MAC_pl_whrv0_total) (line price MAC_pl_whrv_total) (line price MAC_mi_wohrv_total) (line price MAC_mi_whrv0_total) (line price MAC_mi_whrv_total), legend(label(1 "natural") label(2 "plantation-unharvested") label(3 "plantation-harvested (excl. wood product revenue)") label(4 "plantation-harvested (incl. wood product revenue)") label(5 "more cost-effective unharvested") label(6 "more cost-effective harvested (excl. wood product revenue)") label(7 "more cost-effective harvested (incl. wood product revenue)")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))

twoway (line price MAC_mi_whrv_sGr_total) (line price MAC_mi_whrv_sBr_total) (line price MAC_mi_whrv_sBa_total) (line price MAC_mi_whrv_sWa_total) (line price MAC_mi_whrv_total), legend(label(1 "Screened (Griscom)") label(2 "Screened (Brancalion-Tropics only)") label(3 "Screened (Bastin)") label(4 "Screened (Walker)") label(5 "Unscreened")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.75))

twoway (line price MAC_mi_whrv_total) (line price MAC_mi_whrv_sGr_total) (line price MAC_mi_whrv_sGr_bu_total) (line price MAC_mi_whrv_sGr_bu_ad_total), legend(label(1 "Unscreened") label(2 "Screened (Griscom)") label(3 "Screened, Buffered") label(4 "Screened, Buffered, Additional"))  xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") 
	twoway (line price MAC_mi_whrv_sGr_total) (line price MAC_mi_whrv_sGr_bu_total) (line price MAC_mi_whrv_sGr_bu_ad_total), legend(label(1 "Screened (Griscom)") label(2 "Screened, Buffered") label(3 	"Screened, Buffered, Additional"))  xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") 

twoway (line price MAC_mi_whrv_sGr_bu_ad_AMER) (line price MAC_mi_whrv_sGr_bu_ad_AFRI) (line price MAC_mi_whrv_sGr_bu_ad_ASIA) (line price MAC_mi_whrv_sGr_bu_ad_total), legend(label(1 "Latin America") label(2 "Africa") label(3 "Asia") label(4 "All LMIC"))  xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("More cost-effective (screened, buffered, additional)") 

twoway (line price MAC_mi_whrv_sGr_bu_ad_BRA) (line price MAC_mi_whrv_sGr_bu_ad_CHN) (line price MAC_mi_whrv_sGr_bu_ad_IND) (line price MAC_mi_whrv_sGr_bu_ad_MEX) (line price MAC_mi_whrv_sGr_bu_ad_IDN) (line price MAC_mi_whrv_sGr_bu_ad_COL) (line price MAC_mi_whrv_sGr_bu_ad_MMR) (line price MAC_mi_whrv_sGr_bu_ad_COD) (line price MAC_mi_whrv_sGr_bu_ad_THA) (line price MAC_mi_whrv_sGr_bu_ad_VNM)  (line price MAC_mi_whrv_sGr_bu_ad_total), xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)")  legend(label(1 "1. Brazil") label (2 "2. China") label(3 "3. India") label(4 "4. Mexico") label(5 "5. Indonesia") label(6 "6. Colombia") label(7 "7. Myanmar") label(8 "8. DRC") label(9 "9. Thailand") label(10 "10. Vietnam") label(11 "All LMIC (n=138)") ) ylabel(-20(20)100) title("More cost-effective (screened, buffered, additional)") legend(size(*.5))

twoway (line price MAC_mi_whrv_sGr_bu_ad_b1_total) (line price MAC_mi_whrv_sGr_bu_ad_b2_total) (line price MAC_mi_whrv_sGr_bu_ad_b3_total) (line price MAC_mi_whrv_sGr_bu_ad_b4_total) (line price MAC_mi_whrv_sGr_bu_ad_b5_total) (line price MAC_mi_whrv_sGr_bu_ad_b6_total) (line price MAC_mi_whrv_sGr_bu_ad_b7_total) (line price MAC_mi_whrv_sGr_bu_ad_b8_total) (line price MAC_mi_whrv_sGr_bu_ad_b9_total) (line price MAC_mi_whrv_sGr_bu_ad_b10_total) (line price MAC_mi_whrv_sGr_bu_ad_b11_total) (line price MAC_mi_whrv_sGr_bu_ad_b12_total) (line price MAC_mi_whrv_sGr_bu_ad_total), legend(label(1 "Tropical & Subtropical Moist Broadleaf Forests") label(2 "Tropical & Subtropical Dry Broadleaf Forests") label(3 "Tropical & Subtropical Coniferous Forests") label(4 "Temperate Broadleaf & Mixed Forests") label(5 "Temperate Conifer Forests") label(6 "Boreal Forests/Taiga") label(7 "Tropical & Subtropical Grasslands, Savannas & Shrublands") label(8 "Temperate Grasslands, Savannas & Shrublands") label(9 "Flooded Grasslands & Savannas") label(10 "Montane Grasslands & Shrublands") label(11 "Tundra") label(12 "Mediterranean Forests, Woodlands & Scrub") label(13 "Total") ) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("More cost-effective (screened, buffered, additional)") legend(size(*.5))

twoway (line price MAC_mi_whrv_sGr_bu_ad_t1_total) (line price MAC_mi_whrv_sGr_bu_ad_t2_total) (line price MAC_mi_whrv_sGr_bu_ad_t3_total) (line price MAC_mi_whrv_sGr_bu_ad_t4_total) (line price MAC_mi_whrv_sGr_bu_ad_t5_total) (line price MAC_mi_whrv_sGr_bu_ad_t6_total) (line price MAC_mi_whrv_sGr_bu_ad_t7_total) (line price MAC_mi_whrv_sGr_bu_ad_t8_total) (line price MAC_mi_whrv_sGr_bu_ad_total) , legend(label(1 "Natural Regeneration") label(2 "Pinus") label(3 "Cunninghamia") label(4 "Eucalyptus") label(5 "Broadleaf Deciduous") label(6 "Broadleaf Evergreen") label(7 "Needleleaf Deciduous") label(8 "Needleleaf Evergreen") label(9 "Total") ) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("More cost-effective (screened, buffered, additional)")

twoway (line price MAC_nr_wohrv_total) (line price MAC_pl_wohrv_total) (line price MAC_pl_whrv0_total) (line price MAC_pl_whrv_total)  , legend(label(1 "natural") label(2 "plantation-unharvested") label(3 "plantation-harvested (excl. wood product revenue)") label(4 "plantation-harvested (incl. wood product revenue)") ) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))

	twoway (line price MAC_nr_wohrv_total) (line price MAC_pl_wohrv_total) (line price MAC_mi_wohrv_total) , legend(label(1 "natural") label(2 "plantation-unharvested") label(3 "More cost-effective-unharvested")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))

	twoway (line price MAC_nr_wohrv_total) (line price MAC_pl_whrv0_total) (line price MAC_mi_whrv0_total) , legend(label(1 "natural") label(2 "plantation-harvested (excl. wood product revenue)") label(3 "More cost-effective (excl. wood product revenue)")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))
	
twoway (line price MAC_nr_wohrv_total) (line price MAC_pl_whrv_total) (line price MAC_mi_whrv_total) , legend(label(1 "natural") label(2 "plantation-harvested (incl. wood product revenue)") label(3 "More cost-effective (incl. wood product revenue)")) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("All countries") legend(size(*.5))
	

*-----------------
set maxvar 10000
cd "I:\Remote Sensing & GIS Lab\Sandbox\reforestationEconomics\MACCs"
use MACC_total

*Figure 3
gen Gt_nr_wohrv_sGr_bu_ad_total=MAC_nr_wohrv_sGr_bu_ad_total/1000000000
gen Gt_pl_whrv_sGr_bu_ad_total=MAC_pl_whrv_sGr_bu_ad_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_total=MAC_mi_whrv_sGr_bu_ad_total/1000000000

twoway (line price Gt_nr_wohrv_sGr_bu_ad_total) (line price Gt_pl_whrv_sGr_bu_ad_total) (line price Gt_mi_whrv_sGr_bu_ad_total) , legend(label(1 "Natural regeneration") label(2 "Plantation") label(3 "More cost-effective combination")) xtitle("GtCO2") ytitle("$/tCO2") ylabel(-20(20)100) legend(size(*.5))

*Figure S6
gen Gt_mi_whrv_sGr_bu_ad_AMER=MAC_mi_whrv_sGr_bu_ad_AMER/1000000000
gen Gt_mi_whrv_sGr_bu_ad_AFRI=MAC_mi_whrv_sGr_bu_ad_AFRI/1000000000
gen Gt_mi_whrv_sGr_bu_ad_ASIA=MAC_mi_whrv_sGr_bu_ad_ASIA/1000000000

twoway (line price Gt_mi_whrv_sGr_bu_ad_AMER) (line price Gt_mi_whrv_sGr_bu_ad_AFRI) (line price Gt_mi_whrv_sGr_bu_ad_ASIA) (line price Gt_mi_whrv_sGr_bu_ad_total), legend(label(1 "Latin America") label(2 "Africa") label(3 "Asia") label(4 "All LMIC"))  xtitle("tCO2") ytitle("$/tCO2") ylabel(-20(20)100)  

*Figure S7
gen Gt_mi_whrv_sGr_bu_ad_BRA=MAC_mi_whrv_sGr_bu_ad_BRA/1000000000
gen Gt_mi_whrv_sGr_bu_ad_CHN=MAC_mi_whrv_sGr_bu_ad_CHN/1000000000
gen Gt_mi_whrv_sGr_bu_ad_MEX=MAC_mi_whrv_sGr_bu_ad_MEX/1000000000
gen Gt_mi_whrv_sGr_bu_ad_IND=MAC_mi_whrv_sGr_bu_ad_IND/1000000000
gen Gt_mi_whrv_sGr_bu_ad_MMR=MAC_mi_whrv_sGr_bu_ad_MMR/1000000000
gen Gt_mi_whrv_sGr_bu_ad_COL=MAC_mi_whrv_sGr_bu_ad_COL/1000000000
gen Gt_mi_whrv_sGr_bu_ad_IDN=MAC_mi_whrv_sGr_bu_ad_IDN/1000000000
gen Gt_mi_whrv_sGr_bu_ad_THA=MAC_mi_whrv_sGr_bu_ad_THA/1000000000
gen Gt_mi_whrv_sGr_bu_ad_COD=MAC_mi_whrv_sGr_bu_ad_COD/1000000000
gen Gt_mi_whrv_sGr_bu_ad_VEN=MAC_mi_whrv_sGr_bu_ad_VEN/1000000000

twoway (line price Gt_mi_whrv_sGr_bu_ad_BRA) (line price Gt_mi_whrv_sGr_bu_ad_CHN) (line price Gt_mi_whrv_sGr_bu_ad_MEX) (line price Gt_mi_whrv_sGr_bu_ad_IND) (line price Gt_mi_whrv_sGr_bu_ad_MMR) (line price Gt_mi_whrv_sGr_bu_ad_COL) (line price Gt_mi_whrv_sGr_bu_ad_IDN) (line price Gt_mi_whrv_sGr_bu_ad_THA) (line price Gt_mi_whrv_sGr_bu_ad_COD) (line price Gt_mi_whrv_sGr_bu_ad_VEN) , xtitle("GtCO2") ytitle("$/tCO2")  legend(label(1 "1. Brazil") label (2 "2. China") label(3 "3. Mexico") label(4 "4. India") label(5 "5. Myanmar") label(6 "6. Colombia") label(7 "7. Indonesia") label(8 "8. Thailand") label(9 "9. DRC") label(10 "10. Venezuela")  ) ylabel(-20(20)100)  legend(size(*.5))

*Figure S8
gen Gt_mi_whrv_sGr_bu_ad_b1_total=MAC_mi_whrv_sGr_bu_ad_b1_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b2_total=MAC_mi_whrv_sGr_bu_ad_b2_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b3_total=MAC_mi_whrv_sGr_bu_ad_b3_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b4_total=MAC_mi_whrv_sGr_bu_ad_b4_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b5_total=MAC_mi_whrv_sGr_bu_ad_b5_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b6_total=MAC_mi_whrv_sGr_bu_ad_b6_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b7_total=MAC_mi_whrv_sGr_bu_ad_b7_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b8_total=MAC_mi_whrv_sGr_bu_ad_b8_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b9_total=MAC_mi_whrv_sGr_bu_ad_b9_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b10_total=MAC_mi_whrv_sGr_bu_ad_b10_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b11_total=MAC_mi_whrv_sGr_bu_ad_b11_total/1000000000
gen Gt_mi_whrv_sGr_bu_ad_b12_total=MAC_mi_whrv_sGr_bu_ad_b12_total/1000000000

twoway (line price Gt_mi_whrv_sGr_bu_ad_b1_total) (line price Gt_mi_whrv_sGr_bu_ad_b2_total) (line price Gt_mi_whrv_sGr_bu_ad_b3_total) (line price Gt_mi_whrv_sGr_bu_ad_b4_total) (line price Gt_mi_whrv_sGr_bu_ad_b5_total) (line price Gt_mi_whrv_sGr_bu_ad_b6_total) (line price Gt_mi_whrv_sGr_bu_ad_b7_total) (line price Gt_mi_whrv_sGr_bu_ad_b8_total) (line price Gt_mi_whrv_sGr_bu_ad_b9_total) (line price Gt_mi_whrv_sGr_bu_ad_b10_total) (line price Gt_mi_whrv_sGr_bu_ad_b11_total) (line price Gt_mi_whrv_sGr_bu_ad_b12_total) , legend(label(1 "Tropical & Subtropical Moist Broadleaf Forests") label(2 "Tropical & Subtropical Dry Broadleaf Forests") label(3 "Tropical & Subtropical Coniferous Forests") label(4 "Temperate Broadleaf & Mixed Forests") label(5 "Temperate Conifer Forests") label(6 "Boreal Forests/Taiga") label(7 "Tropical & Subtropical Grasslands, Savannas & Shrublands") label(8 "Temperate Grasslands, Savannas & Shrublands") label(9 "Flooded Grasslands & Savannas") label(10 "Montane Grasslands & Shrublands") label(11 "Tundra") label(12 "Mediterranean Forests, Woodlands & Scrub") ) xtitle("GtCO2") ytitle("$/tCO2") ylabel(-20(20)100) legend(size(*.5))

*Figure S9

twoway (line price MAC_mi_whrv_sGr_bu_ad_t1_total) (line price MAC_mi_whrv_sGr_bu_ad_t2_total) (line price MAC_mi_whrv_sGr_bu_ad_t3_total) (line price MAC_mi_whrv_sGr_bu_ad_t4_total) (line price MAC_mi_whrv_sGr_bu_ad_t5_total) (line price MAC_mi_whrv_sGr_bu_ad_t6_total) (line price MAC_mi_whrv_sGr_bu_ad_t7_total) (line price MAC_mi_whrv_sGr_bu_ad_t8_total) (line price MAC_mi_whrv_sGr_bu_ad_total) , legend(label(1 "Natural Regeneration") label(2 "Pinus") label(3 "Cunninghamia") label(4 "Eucalyptus") label(5 "Broadleaf Deciduous") label(6 "Broadleaf Evergreen") label(7 "Needleleaf Deciduous") label(8 "Needleleaf Evergreen") label(9 "Total") ) xtitle("tCO2 (30-year, 5% discounted)") ytitle("$/tCO2 (2020USD)") ylabel(-20(20)100) title("More cost-effective (screened, buffered, additional)")











	
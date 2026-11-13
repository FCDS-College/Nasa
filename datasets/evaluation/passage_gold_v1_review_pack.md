# Passage gold: review pack for the person who verifies

35 drafts written by an AI (me). **Nothing here is verified.** You are the verifier: read each case, decide, then run the command at the end with only the IDs you accept. In each case the text between `**[[ ]]**` is the evidence; the text around it is the rest of that page.

For each answerable case ask three things: (1) does the highlighted text answer the question, (2) is the question clear on its own, (3) would a different page answer it just as well (then it should cite that page too, or be dropped).

Counts: 24 answerable, 11 unanswerable. To report numbers you need at least 20 accepted answerable cases and at least 7 accepted unanswerable ones.

Duplicate and absence checks were re-run on the current corpus (438 pages of 26 reports; the drafts were first checked on 240 pages of 24). No new page repeats a drafted answer; the one new competing figure (PG-010) is flagged below.


---

## PG-001  ·  split: dev  ·  answerable

**Question:** In the vertical upward-burn screening test, what object sits twenty centimetres beneath the holder, and what must the material not do to it?

**Evidence — FF-NTRS-19990063738 page 4:**

> st 1 is the self-extinguishment of a 30-cm-long by 5-cm-wide sample, mounted vertically and ignited chemically at the bottom, before any resulting flame progresses for a distance of 15 cm or beyond (shown as the limiting flame-spread height on Fig. 1). Almost all materials spark or drip flaming particles when ignited. **[[Therefore, in addition to the self-extinguishment criterion, an acceptable material must not ignite a sheet of paper mounted horizontally 20 cm below the sample holder.]]** Typical Test 1 materials are thin sheets, films, foam blocks, and coatings on end-use substrates or on aluminum foil. Test 1 is analogous in principle to the aviation standard method, FAR 25.853, the 12-second vertical Bunsen-burner test for qualifying insulation batts [5]. For space materials, fire resistance is dete

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-002  ·  split: dev  ·  answerable

**Question:** Which atmosphere is treated as the worst case when judging the fire resistance of materials intended for space?

**Evidence — FF-NTRS-19990063738 page 4:**

>  horizontally 20 cm below the sample holder. Typical Test 1 materials are thin sheets, films, foam blocks, and coatings on end-use substrates or on aluminum foil. Test 1 is analogous in principle to the aviation standard method, FAR 25.853, the 12-second vertical Bunsen-burner test for qualifying insulation batts [5]. **[[For space materials, fire resistance is determined within a closed chamber at the worst-case-use oxygen concentration and pressure environment, currently 30- vol% oxygen in nitrogen at 70.3 kPa [6].]]** This atmos- phere corresponds to the Shuttle and International Space Station (ISS) environments that are prescribed for crew conditioning prior to extravehicular activities, or that may be encountered as the maximum tolerance level in emergencies. Test 4, illustrated in Fig. 2, is an adaptation of Test 1 to evaluate t

**Evidence — FF-NTRS-20000034017 page 10:**

> rements utilizing the NSTS 1700.7 document (29). The ISS Addendum requirements are per paragraph 209.2b "Other Habitable Area". In addition to the original paragraph, the addendum requires the following: • The ISS worst-case operating environment is [105 kPa] with 24.1 percent oxygen for all locations except airlocks. **[[Airlock worst-case environment is [70.3 kPa] with 30 percent oxygen.]]** Payloads are only required to test materials in the worst-case airlock environment if [intended] to operate in the airlock during EVA (extravehicular activity by the flight crew) preparations. Material test methods and standards for the ISS modules and payloads are, at this time, identical to those of the Shuttle. A s

**My recommendation: look closely.** the second page (20000034017 p10) gives two environments: ISS worst case 105 kPa / 24.1 % O2 for all places except airlocks, and 70.3 kPa / 30 % O2 for airlocks. Keep p10 as evidence, or drop it?

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-003  ·  split: dev  ·  answerable

**Question:** How many seconds of microgravity do the two free-fall facilities at NASA Glenn provide?

**Evidence — FF-NTRS-20000034017 page 7:**

> ant environments are common, but experimental verifications, necessary for fire-safety applications, are not easy to obtain (10). Opportunities for flight tests on the Shuttle and space stations are quite limited. Most experimental microgravity combustion studies to date have been conducted in ground-based facilities. **[[The principal venues are the two free-fall drop towers at the NASA Glenn Research Center, which provide 2.2 and 5.2 sec each of microgravity conditions of the order of 10-4 g, where g is the sea-level acceleration of 9.8 m/s-" (11).]]** Other facilities are aircraft flying parabolic (Keplerian) trajectories, which allow up to 20 sec of low-gravity time, at significantly higher residual-gravity levels in the range of 10-2 g. Sounding rockets can increase the low-gravity exposures to 5 to 15 rain or longer at residual gravity levels of the order of 10-

**My recommendation: look closely.** other reports mention '~5 s' drop times in general; this question is about the two NASA Glenn towers (2.2 s and 5.2 s). Probably fine.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-004  ·  split: dev  ·  answerable

**Question:** For how long can airplanes flying parabolic arcs give low gravity, and how large is the leftover acceleration?

**Evidence — FF-NTRS-20000034017 page 7:**

> icrogravity combustion studies to date have been conducted in ground-based facilities. The principal venues are the two free-fall drop towers at the NASA Glenn Research Center, which provide 2.2 and 5.2 sec each of microgravity conditions of the order of 10-4 g, where g is the sea-level acceleration of 9.8 m/s-" (11). **[[Other facilities are aircraft flying parabolic (Keplerian) trajectories, which allow up to 20 sec of low-gravity time, at significantly higher residual-gravity levels in the range of 10-2 g.]]** Sounding rockets can increase the low-gravity exposures to 5 to 15 rain or longer at residual gravity levels of the order of 10-4 g. The first fire-safety related microgravity combustion experiments were performed in 1966 aboard a KC-135 aircraft laboratory (12). Ignition susceptibility was found to be similar to that

**My recommendation: look closely.** other reports mention '±0.02 g' jitter for ~20 s flights; the answer here is '20 s, about 10-2 g'. Probably fine.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-005  ·  split: dev  ·  answerable

**Question:** Apart from microgravity, which fractions of Earth gravity will the aircraft test campaign reproduce?

**Evidence — FF-NTRS-20040161216 page 2:**

> electrical fires.  **[[Tests will be conducted at the lowest gravity level possible in NASA’s Reduced- Gravity Aircraft, as well as at Lunar (0.16 g) and Martian (0.38 g) levels.]]**  The Fire Suppression Testing Facility (FSTF) that will be built and used for this investigation may in the future serve as a prototype for the development of a Fire Suppression Insert that may use the Combustion Integrated Rack onboard the ISS to conduct long-duration µg tests.  This insert will be capable of pro

**Evidence — FF-NTRS-20040161216 page 10:**

> PARTIAL GRAVITY TESTING Fire Suppression Insert Combustion Integrated Rack (CIR) CURRENT TESTING: **[[KC-135 Parabolic flights (0.01, 0.16, 0.38 g)]]** Î RESEARCH POTENTIAL • Current Low-Gravity Testing Facility could be used as prototype for a Fire Suppression Insert in the Combustion Integrated Rack (CIR) onboard the ISS • Testing under long durations of Pg could provide a demonstration of a fire-suppression system prototype under spaceflight conditions (Technolo

**My recommendation: look closely.** the second page only lists '0.01, 0.16, 0.38 g' without saying lunar or Martian.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-006  ·  split: dev  ·  answerable

**Question:** How far apart are the two plates set in the usual Narrow Channel Facility arrangement?

**Evidence — FF-NTRS-20070010766 page 6:**

> orces and there is no buoyancy-driven convection within the cavity thereby simulating a low-g environment. For horizontal plates heated from below, the value of the critical Rayleigh number is approximately 1708.13 Using T1=900 deg C and T2=80 deg C, the plate separation distance, L, that yields Rac=1708 is 1.1 cm. **[[Accordingly, the plate separation typically used in the Narrow Channel Facility is 1.0 cm configuration.]]** The Narrow Channel Facility can measure the flame spread rate and the propensity for flame propagation at a specific flow velocity, pressure, and oxygen concentration14 (PI: Dr. F. J. Miller, National Center for Space Exploration Research (NCSER)). The primary question being examined at this time is whether the dis

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-007  ·  split: dev  ·  answerable

**Question:** What total pressure and oxygen share are proposed for the cabin of future exploration vehicles?

**Evidence — FF-NTRS-20080012607 page 1:**

> ey, CA 94720, USA. bNASA John H Glenn Research Center, Cleveland, OH 44256   ABSTRACT In order to reduce the risk of decompression sickness associated with spacewalks, NASA is considering designing the next generation of exploration vehicles and habitats with a different cabin environment than used previously.  **[[The proposed environment uses a total cabin pressure of 52.7 to 58.6 kPa with an oxygen concentration of 30 to 34% by volume and was chosen with material flammability in mind.]]**  Because materials may burn differently under these conditions and there is little information on how this new environment affects the flammability of the materials onboard, it is important to conduct material flammability experiments at the intended exploration atmosphere.  One method to evaluate material flammabi

**Evidence — FF-NTRS-20080012607 page 2:**

>  has been done using standard atmospheric conditions - 101kPa with 21% oxygen by volume.  However, NASA is designing the next generation of vehicles to operate with a different cabin environment to reduce the risk of decompression sickness and the pre-breath time required for extra-vehicular activities (EVA) [10].  **[[The proposed space exploration atmosphere (SEA) uses a total cabin pressure of 52.7 to 58.6 kPa with an oxygen concentration of 30 to 34% by volume.]]**  It is well known that an increase in oxygen concentration can decrease the ignition delay time [11-13], but the influence of pressure is not well explored.  The effect of pressure on the autoignition of polymers has been examined by several researchers, including Kishore and Sankaralingam [14], Hermance [15], Att

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-008  ·  split: dev  ·  answerable

**Question:** By roughly what share did lowering the pressure at normal oxygen shorten the time for a sample to ignite?

**Evidence — FF-NTRS-20080012607 page 1:**

> of pressure and oxygen concentration on the ignition delay.  Tests were conducted for a baseline case of normal pressure and oxygen concentration, low pressure (58.6 kPa) with normal oxygen (21%).  Future work will focus on low pressure with 32% oxygen concentration (space exploration atmosphere - SEA) conditions.  **[[It was found that reducing the pressure while keeping the oxygen concentration at 21% reduced the ignition time by 17% on average.]]**  It was also noted that the critical heat flux for ignition decreases in low-pressure conditions.  Because tests conducted in standard atmospheric conditions will underpredict the flammability of materials intended for use on spacecraft, fire safety onboard at exploration atmospheres may be compromised.  INTROD

**Evidence — FF-NTRS-20080012607 page 4:**

> ime as a function of externally applied heat flux for several oxidizer flow velocities under 58.6 kPa and 21% O2  Figure 4 compares the ignition delay time as a function of externally applied heat fluxes for the difference environments tested.  In all plots, the piloted ignition time is shorter at low pressures.  **[[The ignition delay time decreases on average by 17% when the pressure is reduced compared to standard atmospheric conditions.]]**  If the data is extrapolated to infinitely long ignition times (when the inverse of the square root of the ignition time is equal to zero), the critical heat flux for ignition can be approximately determined [13].  From Fig. 4, it is inferred that the critical heat flux decreases when the pressure is reduced.  It i

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-009  ·  split: dev  ·  answerable

**Question:** How much more oxygen can the limiting threshold be at normal gravity than in weightlessness?

**Evidence — FF-NTRS-20080034883 page 5:**

> ad were performed in a low-speed flow tunnel to simulate spacecraft ventilation flows. Three thin fuels were tested for flammability (Ultem 1000 (General Electric Company), 10 mil film, Nomex (Dupont) HT90-40, and Mylar G (Dupont) and one fuel for flame spread testing (Kimwipes (Kimberly-Clark Worldwide, Inc.). **[[The 1g Upward Limiting Oxygen Index (ULOI) and 1g Maximum Oxygen Concentration (MOC) are found to be greater than those in 0g, by up to 4% oxygen mole fraction, meaning that the fuels burned in 0g at lower oxygen concen- trations than they did using the NASA Standard 6001 Test 1 protocol.]]** Flame spread tests with Kimwipes were used to develop correlations that capture the effects of flow velocity, oxygen concentration, and pressure on flame spread rate. These correlations were used to determine that over virtually the entire range of spacecraft atmospheres and flow conditions, the opposed spread 

**Evidence — FF-NTRS-20080034883 page 11:**

> nough that flame spread rates could be obtained in the short microgravity time. This was the first time that two of the fuels, Ultem 1000 and Mylar G), were tested in a microgravity environment. The 1g ULOI and 1g MOC flammability limits obtained from NASA Test 1 are compared to 0g limits for the same fuel width. **[[The 1g ULOI and 1g MOC are found to be greater than those in 0g, by up to 4% oxygen mole fraction]]**, meaning that the fuels burned in 0g at lower oxygen concen- trations than they did using the Test 1 protocol. While test times in 0g are limited to 5.18 sec, these test data provide a conservative estimate of the material’s flammability in 0g. The flame spread tests were used to develop correlations that capture

**Evidence — FF-NTRS-20080034883 page 13:**

>  spread were performed in a low-speed flow tunnel to simulate spacecraft ventilation flows. Three thin fuels were tested for flammability (Ultem 1000 (General Electric Company), 10 mil film, Nomex (Dupont) HT90-40, and Mylar G (Dupont) and one fuel for flame spread testing (Kimwipes (Kimberly-Clark Worldwide, Inc.). **[[The 1g Upward Limiting Oxygen Index (ULOI) and 1g Maximum Oxygen Concentration (MOC) are found to be greater than those in 0g, by up to 4% oxygen mole fraction]]**, meaning that the fuels burned in 0g at lower oxygen concentrations than they did using the NASA Standard 6001 Test 1 protocol. Flame spread tests with Kimwipes were used to develop correlations that capture the effects of flow velocity, oxygen concentration, and pressure on flame spread rate. These correlations we

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-010  ·  split: dev  ·  answerable

**Question:** What is the highest oxygen concentration that can be allowed at sea-level cabin pressure (14.7 psia) without invalidating the certification of some materials?

**Evidence — FF-NTRS-20110008636 page 2:**

> ata indicate there is an approximately linear dependence of MOCs on total pressure Pt having the form:   MOC = m Pt + b (1)  The values for the slope, m, and intercept, b, were determined. The maximum slope was -0.975% oxygen/psia and the minimum was -0.251% oxygen/psia, with an average of -0.607% oxygen/psia. **[[It was recommended to use only the minimum MOC, i.e., 25.6% oxygen as a conservative estimate, indicating that the oxygen concentration limit at 14.7 psia cannot be set higher than approximately 25.6% oxygen without invalidating the material’s flammability certification in 30% oxygen at 10.2 psia for at least some materials.]]** For testing performed in the mid to late 80s while upgrading the Space Shuttle from 25.9% oxygen at 14.7 psia to 30% oxygen at 10.2 psia, there was an underlying assumption that 30% oxygen at 10.2 psia would provide a more flammable environment than conditions of 25.9% oxygen at 14.7 psia. For at least one of the m

**My recommendation: look closely.** another report (20070021223 p2) states '25.9 % oxygen at 14.7 psia' as the historical Shuttle/ISS limit. The question asks for the conservative ceiling that does not invalidate certifications (25.6 %, cited page). Is the question precise enough to exclude 25.9 %?

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-011  ·  split: dev  ·  answerable

**Question:** Below what oxygen fraction do burning methanol droplets stop, in the carbon dioxide and helium dilution experiments?

**Evidence — FF-NTRS-20130014061 page 1:**

> diameters. Simpliﬁed theoretical models correlate the measured burning rate constant and the ﬂame standoff ratio reasonably well. An activation energy asymptotic theory accounting for time-dependent water dissolution or evaporation from the droplet is shown to predict the measured diffusive extinction conditions well. **[[The experiments also show that the limiting oxygen index for methanol in these diluent gases is around 12% to 13% oxygen by volume.]]** 1 Introduction Studies of droplet combustion are of interest from both fundamental and applied viewpoints, the latter in connection with both combustor performance and safety issues. Inﬂuences of carbon diox- ide and helium, as well as increased nitrogen, in the atmosphere on the combustion characteristics and on exti

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-012  ·  split: validation  ·  answerable

**Question:** What power of fire in a capsule would be enough to burn the crew's airways and skin?

**Evidence — FF-NTRS-20140006580 page 3:**

> ork5 considered the threats to the crew due to tracheal and skin burning, oxygen depletion, carbon monoxide and carbon dioxide production as well as hyperthermia and vehicle over-pressurization. The analysis considered a sealed volume the approximate size of the Destiny module on the International Space Station (ISS). **[[The results showed that ﬁres between 50 and 100 kW could result in tracheal and skin burns to the crew.]]** The analysis, however, did not consider any mitigation of the threat due to the safety systems of the spacecraft. One of the primary safety systems is the positive pressure relief valves (PPRVs) that will act to protect the vehicle structure from over-pressurization. In the event of an accidental ﬁre, the heat release

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-013  ·  split: validation  ·  answerable

**Question:** What peak pressure and temperature would the cabin reach in the fire scenario if no relief valve vented the gas?

**Evidence — FF-NTRS-20140006580 page 6:**

> he case presented in our previous work.5 The ﬁre growth is according to the following relationship typical of terrestrial ﬁres. ˙Q = α t2 (7) The total mass of fuel burned is approximately 3.0 kg and the peak ﬁre power is nearly 200 kW. The results clearly show how the PPRV mitigates the hazard of over-pressurization. **[[Without a relief valve, the peak pressure and temperature inside the cabin is over 1.6 atm and 475 K, respectively.]]** This could result in damage to the vehicle and a signiﬁcant threat to the crew. The PPRV, however, clearly mitigates the hazard by venting gas to attempt to maintain the pressure at 1.0 atm. The results show that for all of the simulations in Figure 1 the results early in the ﬂame lifetime are similar. The ﬁres start 

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-014  ·  split: validation  ·  answerable

**Question:** What is the greatest sample thickness advised for the present igniter in the upward flammability test?

**Evidence — FF-NTRS-20150004099 page 1:**

> d that determines the minimum safe total pressure for a material within the constant partial pressure control band. Then, increasing this pressure limit by a factor of safety, we can define the material as being safe to use at the NULP + SF (where SF is on the order of 10 kPa, based on existing flammability data).  **[[It is recommended that the thickest material to be tested with the current Test 1 igniter should be 3 mm thick (1/8”) to avoid the problem of differentiating between an ignition limit and a true flammability limit.]]** Nomenclature αs =  thermal diffusivity of the solid  l = burn length, cm L = burn length non-dimensionalized with 15.2 cm, Test 1 length criterion ℓ = characteristic thickness of the solid MOC = maximum oxygen concentration where all samples tested (at least five) pass the Test 1 criteria N = integer n

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-015  ·  split: validation  ·  answerable

**Question:** How is the upward limiting oxygen concentration defined?

**Evidence — FF-NTRS-20150004099 page 1:**

> er number of Test 1 tests NULP = Normoxic Upward Limiting Pressure μNULP = NULP + SF, the microgravity normoxic upward limiting pressure O2 = Oxygen percentage by volume p = average probability of observing a burn in a Test 1 test (material fails test)  = maximum likelihood estimate of p from a set of data. **[[q = probability of not observing a burn in Test 1 = 1-p SF = safety factor to account for enhanced flammability in spacecraft t = time ULOI = upward limiting oxygen concentration where ~ 50 % of samples fail the Test 1 criteria Vf = flame spread rate x = integer number of actual observed burns λ = mean number of burns observed in a given number of tests.]]**  = Np, also the variance of the distribution  = maximum likelihood estimate of λ from a set of data. = N σ = standard deviation for number of burns observed = (Npq)1/2 τ = characteristic time of process  1 Spacecraft Fire Safety Research, 21000 Brookpark

**My recommendation: look closely.** the cited span is a whole nomenclature list; only the 'ULOI = ...' entry answers the question.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-016  ·  split: validation  ·  answerable

**Question:** What fixed amount of heat per gram of oxygen was used to turn oxygen consumption into heat release?

**Evidence — FF-NTRS-20150019858 page 1:**

> ness of the combustion.    The oxygen and carbon dioxide readings before and after each test were analyzed and compared very well to stoichiometric ratios for a one step gas-phase reaction. The CO versus CO2 followed a linear trend for some datasets, but not for all the different geometries of fuel and flow tested. **[[We calculated the heat release rates during each test from the oxygen consumption and burn times, using the constant 13.1 kJ of heat released per gram of oxygen consumed.]]**  The results showed that the majority of the tests had heat release rates well below 100 Watts.   Lastly, the global equivalence ratio for the tests is estimated to be fuel rich: 1.3 on average using mass loss and oxygen consumption data.  1 Dr., Combustion

**Evidence — FF-NTRS-20150019858 page 7:**

> acecraft Maximum Allowable Concentration) values for even long term exposure (10 ppm), let alone the 1 hour SMAC of 55 ppm [11].  Lastly, the heat release rates (HRR) from these small microgravity fires can be estimated using Huggett’s oxygen consumption calorimetry [12] and the burn time for each test.  **[[Using his constant of 13.1 kJ/g O2, we estimate the heat release rate to be typically well below 100 W]]**, as shown in Figure 8.   There is a trend of increasing HRR with increasing ambient oxygen concentration, and the scatter is attributed to the different duct flows between and even within the tests.  The one long opposed thick slab test that caused the lower downstream corner of the front window damage rele

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-017  ·  split: holdout  ·  answerable

**Question:** What are the dimensions of the transparent tube forming the test section of the radiant-heating rig?

**Evidence — FF-NTRS-20150023467 page 3:**

> yze under the influence of the external radiant flux or while burning. The apparatus was built to be similar in most respects to the ASTM D2863 - 12 1 standard, and thus the inlet to the test section is filled with borosilicate beads which act to homogenize the flow and produce a uniform flow into the test section. **[[The test section itself is a 254 mm piece of quartz tubing with an outer diameter of 75 mm and an inner diameter of 70 mm.]]** The samples are centered in the test section radially as well as along the lit length of the heaters. The quartz infrared halogen lamp heaters have a lit length of 127 mm and a total length of 220 mm that are enclosed in parabolic reflectors. The three heaters are radially equispaced around the test section at 120 

**My recommendation: look closely.** 'transparent tube' is my reading of 'quartz tubing'.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-018  ·  split: holdout  ·  answerable

**Question:** Where is the electrically heated pilot placed relative to the fuel sample?

**Evidence — FF-NTRS-20150023467 page 3:**

> frared halogen lamp heaters have a lit length of 127 mm and a total length of 220 mm that are enclosed in parabolic reflectors. The three heaters are radially equispaced around the test section at 120 degree intervals, thus irradiating the fuel sample with an approximately uniform heat flux of upwards of 40 kW/m^2. **[[Ignition is induced with an electrically heated Kanthal wire coil that acts as a pilot and is located 25 mm downstream from the trailing edge of the fuel sample.]]**  The coil is placed so that it covers the fuel vapor concentration boundary layer thus eliminating the pilot location, in the axial direction, as a parameter of the problem. Surface temperature of the samples is measured with 0.127 mm wire thickness type K thermocouples placed halfway along the length of the test s

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-019  ·  split: holdout  ·  answerable

**Question:** Which range of rod widths was burned in the cast acrylic experiments at low oxygen?

**Evidence — FF-NTRS-20160012691 page 1:**

> simple way to measure normal gravity blowoff limits to compare with microgravity Burning and Suppression of Solids – II (BASS-II) results recently obtained aboard the International Space Station.  This testing utilized the same BASS-II concurrent rod geometry, but with the addition of normal gravity buoyant flow.   **[[Cast polymethylmethacrylate (PMMA) rods of diameters ranging from 0.635 cm to 3.81 cm were burned at oxygen concentrations ranging from 14 to 18% by volume.]]**  The forced flow velocity where blowoff occurred was determined for each rod size and oxygen concentration. These blowoff limits compare favorably with the BASS-II results when the buoyant stretch is included and the flow is corrected by considering the blockage factor of the fuel.  From these results, the normal g

**My recommendation: look closely.** 'rod widths' stands for 'diameters'.

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-020  ·  split: holdout  ·  answerable

**Question:** What limiting oxygen levels and flame temperatures were seen for the larger hydrocarbon fuels?

**Evidence — FF-NTRS-20160012691 page 1:**

> ability in low gravity.  Keywords: Blowoff, Axisymmetric, Stagnation, PMMA rod  1. Introduction  Early work [1] on flammability limits has demonstrated that a hemispherical stagnation flow geometry is a good way to obtain the flammability limits of various fuels as a function of upward flowing oxidizer gas.  **[[Many heavier hydrocarbons were found to have similar limiting oxygen concentrations (13%-14%) and flame temperatures (1450-1500oC).]]**  The stagnation flow geometry is amenable to asymptotic analyses [2, 3], numerical modeling [4-6], and experimental extinction work for both axisymmetric and 2D geometries [7-11].  Recent testing completed on the International Space Station investigated the oxygen-flow flammability boundary for three different ca

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-021  ·  split: validation  ·  answerable

**Question:** What fabric is the sample material for the first and third spaceflight fire experiments made of?

**Evidence — FF-NTRS-20170001636 page 2:**

> stowage straps used in the Cygnus vehicle. This duct will provide a uniform flow across the samples, maintain a clear flow path within the experiment module, and prevent burning debris from interacting with the rest of the cargo. The sample card is positioned in the center of the flow duct as shown in Fig. 1.  **[[2.1 Sample Materials The sample material for Saffire-I and III is a composite fabric consisting of cotton on a fiberglass substrate (75% cotton, 25% fiberglass by weight).]]** It is called SIBAL cloth because it was developed for the Solid Inflammability Boundary at Low-Speeds (SIBAL) spaceflight experiment and has been used in many space experiments because it burns like cotton but maintains structural integrity after the cotton is consumed. The objective of the Saffire-I and III tes

**Evidence — FF-NTRS-20170000230 page 4:**

>  have normal- gravity flammability limits near 21% oxygen by volume.4-6 Camera images are the primary diagnostics for these tests as the intended result is primarily to determine whether the flame propagates or self-extinguishes. If it propagates, additional data such as flame spread rate will be obtained.     **[[a. Saffire-I and -III sample card. The b. Saffire-II sample card. Card sample is a composite fabric  contains nine samples (5 cm x 29 (75% cotton – 25% fiberglass by]]**  cm) of PMMA (flat and structured)  mass) and is0.4 m wide x 0.95 m long.  Silicone (3 thicknesses, different ignition direction), composite fabric from Saffire-I, III, and Nomex (with PMMA ignition)  Figure 2.  Sample cards for the Saffire-I, II, and III experiments.

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-022  ·  split: validation  ·  answerable

**Question:** At which air speeds will the first and the third spaceflight fire experiments be run?

**Evidence — FF-NTRS-20170001636 page 2:**

> riment and has been used in many space experiments because it burns like cotton but maintains structural integrity after the cotton is consumed. The objective of the Saffire-I and III tests will be to determine how rapidly a large-scale fire grows in low- gravity and whether it reaches a steady-state spread rate. **[[Saffire-I will be conducted at an air flow velocity of 20 cm/s while Saffire-III will be run at a flow velocity of 30 cm/s .]]**  Saffire-II has a sample card that contains 9 samples, each 5 cm x 29 cm. Table 1 lists the samples contained on Saffire-II while Fig. 2 shows their locations on the sample card. These materials were selected because they have normal gravity Maximum Oxygen Concentration (MOC) flammability limits that indicate t

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-023  ·  split: validation  ·  answerable

**Question:** How wide is the insert that holds the burners in the combustion experiment chamber?

**Evidence — FF-NTRS-20210021781 page 4:**

> 4 of 11  Fig. 2 CIR facility returned to its normal configuration by Japanese astronaut Norishige Kanai [ISS055e096658]  **[[ACME’s chamber insert, which is ~0.4 m in diameter, provides common mounting for a variety of burners (but only one at a time) on the chamber axis.]]**  Tests have been conducted with gas-jet, coflow, and spherical burners, in addition to a fourth type developed for the Burning Rate Emulator (BRE) investigation.  The resistively-heated igniter has a crew- exchangeable tip and arm (to accommodate the various burners) and its stepper-motor drive allows for precise pos

**Evidence — FF-NTRS-20140009169 page 7:**

> 7  **[[ACME’s chamber insert, which is ~0.4 m in diameter, provides common mounting for a variety of burners on the chamber axis (but only one at a time) and includes a retracting resistive igniter.]]** As depicted in Figure 3, there will initially be gas-jet burners (with inner diameters ranging from 0.4 to 3.2 mm), a small coflow burner (where the two concentric tubes have inner diameters of 2.1 and 25 mm), porous spherical burners (with diameters ranging from 6.35 to 12.7 mm), and two flat porous burners for 

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-024  ·  split: validation  ·  answerable

**Question:** Low-momentum microgravity flames burned for minutes at elevated oxygen; below what oxygen level did they go out by themselves?

**Evidence — FF-NTRS-20210021781 page 7:**

>  temperature, and smoke point.  Testing included atmospheres with elevated oxygen concentrations and reduced pressures being considered for future crew vehicles.  An example dome-shaped flame can be seen in Fig. 7. Low-momentum microgravity flames can burn for minutes in the absence of an air flow or flame spread.  **[[While the flames can burn for minutes in elevated oxygen concentrations, like those being considered for future spacecraft, they were found to self-extinguish in concentrations below ~25% (by volume).]]**  While smaller flames can burn for minutes at elevated oxygen concentrations, larger flames were generally seen to self-extinguish within 1.5 minutes.  While ethylene flames at elevated oxygen concentrations can burn for minutes, methane flames were seen to self-extinguish within a minute.  Fig. 7 Pure ethylene 

**My recommendation: accept** (no problem found in the pre-screen).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-025  ·  split: dev  ·  unanswerable (in_domain_not_in_corpus)

**Question:** What ignition temperature was measured for hydrazine propellant leaking into a spacecraft cabin?

**Check done:** `hydrazine` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-026  ·  split: dev  ·  unanswerable (in_domain_not_in_corpus)

**Question:** How does aerogel insulation change the flammability of spacecraft wall panels?

**Check done:** `aerogel` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-027  ·  split: dev  ·  unanswerable (in_domain_not_in_corpus)

**Question:** At what oxygen concentration can simulated lunar regolith sustain a flame?

**Check done:** `regolith` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-028  ·  split: validation  ·  unanswerable (in_domain_not_in_corpus)

**Question:** How well does a fire blanket suppress an electrical fire in orbit?

**Check done:** `fire blanket` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-029  ·  split: validation  ·  unanswerable (in_domain_not_in_corpus)

**Question:** How quickly does a lithium-ion battery fire spread in microgravity?

**Check done:** `lithium.ion` occurs on 0 of 438 indexable pages (the word `lithium` does occur once, in `lithium hydroxide`, the CO2 canister in the Apollo 204 report: not a battery). That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-030  ·  split: holdout  ·  unanswerable (in_domain_not_in_corpus)

**Question:** What oxygen pressure ignites titanium structural tubing during a spacecraft fire?

**Check done:** `titanium` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-031  ·  split: holdout  ·  unanswerable (in_domain_not_in_corpus)

**Question:** What is the flame spread rate over kerosene-soaked fabric in reduced gravity?

**Check done:** `kerosene` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-032  ·  split: dev  ·  unanswerable (in_domain_not_in_corpus)

**Question:** What fire safety requirements apply to the Artemis lunar Gateway station?

**Check done:** `artemis|gateway` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-033  ·  split: dev  ·  unanswerable (out_of_domain)

**Question:** What is a good recipe for a chocolate cake?

**Check done:** `chocolate` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-034  ·  split: validation  ·  unanswerable (out_of_domain)

**Question:** Who won the football World Cup in 2018?

**Check done:** `football` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## PG-035  ·  split: holdout  ·  unanswerable (out_of_domain)

**Question:** How do I renew a driving licence in Egypt?

**Check done:** `driving licen` occurs on 0 of 438 indexable pages. That shows the topic is not mentioned, not that no passage answers the question in other words.

**My recommendation: accept if you agree the reports do not answer it** (guidelines §5.3 prefer a person to write these, so rewrite any that read as machine-made).

**Your decision:** [ ] accept   [ ] reject   notes: 


---

## When you are done

Remove the IDs you rejected from this command and run it in PowerShell from the repo folder, with your own name:

```powershell
python -m ai.rag.evaluation.adopt_drafts --verifier "Your Name" --accept PG-001 PG-002 PG-003 PG-004 PG-005 PG-006 PG-007 PG-008 PG-009 PG-010 PG-011 PG-012 PG-013 PG-014 PG-015 PG-016 PG-017 PG-018 PG-019 PG-020 PG-021 PG-022 PG-023 PG-024 PG-025 PG-026 PG-027 PG-028 PG-029 PG-030 PG-031 PG-032 PG-033 PG-034 PG-035
```

It writes `datasets\evaluation\passage_gold_v1.jsonl`; commit it and open a pull request. It refuses an AI-looking name, the cases' author and a selection that would break the rules (exact evidence text, splits by document, at least 25 % unanswerable).

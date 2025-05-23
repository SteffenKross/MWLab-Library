import gdsfactory as gf
import lnoi400
from gplugins.common.config import PATH
from gdsfactory.typings import CrossSectionSpec
from lnoi400.spline import bend_S_spline_varying_width

#####################
# Asymmetric directional coupler
#####################
gf.clear_cache()
@gf.cell
def asymmetric_directional_coupler(
    io_wg_sep: float = 30.6,
    sbend_length: float = 58,
    central_straight_length: float = 16.92,
    coupl_wg_sep: float = 1.5,
    coup_wg_width: float = 1.0,
    taper_npoints: int = 201,
    cross_section_io: CrossSectionSpec = "xs_rwg1000",
) -> gf.Component:
    """Returns a 50-50 directional coupler. Default parameters give a 50/50 splitting at 1550 nm.

    Args:
        io_wg_sep: Separation of the two straights at the input/output, top-to-top.
        sbend_length: length of the s-bend part.
        central_straight_length: length of the coupling region.
        coupl_wg_sep: Distance between two waveguides in the coupling region (side to side).
        cross_section_io: cross section spec at the i/o (must be defined in tech.py).
        coup_wg_width: waveguide width at the coupling section.
    """

    s0 = gf.Section(
        width=coup_wg_width,
        offset=0,
        layer="LN_RIDGE",
        name="_default",
        port_names=("o1", "o2"),
    )
    s1 = gf.Section(
        width=10.0, 
        offset=0, 
        layer="LN_SLAB", 
        name="slab", 
        simplify=0.03
    )
    
    cross_section_coupling = gf.CrossSection(sections=[s0, s1])
    cross_section_io = gf.get_cross_section(cross_section_io)

    s_height = (
        io_wg_sep - coupl_wg_sep - coup_wg_width
    ) / 2  # take into account the width of the waveguide
    size = (sbend_length, s_height)

    # s-bend settings
    settings_s_bend = {
        "size": size,
        "cross_section1": cross_section_coupling,
        "cross_section2": cross_section_io,
        "npoints": 201,
    }
    dc = gf.Component()

    # top right branch
    
    c_tr = dc << lnoi400.cells.bend_S_spline_varying_width(
        size= (sbend_length, 0), cross_section1="xs_rwg1000", cross_section2="xs_rwg3000", npoints=taper_npoints
    )
    c_tr.dmove(
        c_tr.ports["o1"].dcenter, (central_straight_length / 2, 
                                   0.5 * (coupl_wg_sep + coup_wg_width)),
    )
    
    # bottom right branch
    c_br = dc << bend_S_spline_varying_width(**settings_s_bend)
    c_br.dmirror_y()
    c_br.dmove(
        c_br.ports["o1"].dcenter,
        (central_straight_length / 2, -0.5 * (coupl_wg_sep + coup_wg_width)),
    )
    gf.components.taper
    # central waveguide
    straight_center_up = dc << gf.components.straight(
        length=central_straight_length, cross_section=cross_section_io
    )
    straight_center_up.connect("o2", c_tr.ports["o1"])

    straight_center_down = dc << gf.components.straight(
        length=central_straight_length, cross_section=cross_section_coupling
    )
    straight_center_down.connect("o2", c_br.ports["o1"])

    # top left branch
    c_tl = dc << lnoi400.cells.bend_S_spline_varying_width(
        size= (sbend_length, 0), cross_section1="xs_rwg3000", cross_section2="xs_rwg1000", npoints=taper_npoints
    )
    c_tl.dmove(
        c_tl.ports["o1"].dcenter, (- sbend_length - central_straight_length / 2, 
                                   0.5 * (coupl_wg_sep + coup_wg_width)),
    )

    # bottom left branch
    c_bl = dc << bend_S_spline_varying_width(**settings_s_bend)
    c_bl.dmirror_x()
    c_bl.dmirror_y()
    c_bl.dmove(c_bl.ports["o1"].dcenter, straight_center_down.ports["o1"].dcenter)

    # Expose the ports
    exposed_ports = [
        ("o1", c_bl.ports["o2"]),
        ("o2", c_tl.ports["o2"]),
        ("o3", c_tr.ports["o2"]),
        ("o4", c_br.ports["o2"]),
    ]

    [dc.add_port(name=name, port=port) for name, port in exposed_ports]
    return dc


#######
# NEW #
#######

#####################
# Traveling Wave EOM
#####################

@gf.cell
def tWave_EOM():

    mzm = gf.Component()

    # trail_cpw variables
    rf_central_conductor_width = 21.0
    rf_gap = 4
    modulation_length = 4330.0

    # mzm_unbalanced variables
    length_imbalance = 0.0
    lbend_tune_arm_reff = 75.0
    rf_pad_start_width = 80.0
    rf_ground_planes_width = 180.0
    rf_pad_length_straight = 10.0
    rf_pad_length_tapered = 300.0
    bias_tuning_section_length = 700.0
    cpw_cell = lnoi400.cells.trail_cpw
    with_heater = True
    heater_offset = 1.2
    heater_width = 1.0
    heater_pad_size = (75.0, 75.0)

    # #_mzm_interferometer variables
    taper_length = 100.0
    rib_core_width_modulator = 2.5

    

    rf_line = mzm << cpw_cell(length = modulation_length,
                                signal_width = rf_central_conductor_width,
                                gap_width = rf_gap,
                                th = 3.0,            #h
                                tl = 44.7,           #r
                                tw = 7.0,            #t
                                tt = 1.5,            #s
                                tc = 5.0,            #c
                                ground_planes_width = 180.0,
                                rounding_radius = 0.5,
                                bondpad={
                                        "component": "CPW_pad_linear",
                                         "settings": {
                                                    "start_width": rf_pad_start_width,
                                                    "length_straight": rf_pad_length_straight,
                                                    "length_tapered": rf_pad_length_tapered,
                                    },
                                })
    # default code
    rf_line.dmove(rf_line.ports["e1"].dcenter, (0.0, 0.0))


    # Interferometer subcell

    splitter1 = lnoi400.cells.mmi1x2_optimized1550()
    splitter2 = lnoi400.cells.mmi2x2_optimized1550()

    sbend_large_AR = 3.6

    gap_eff = rf_gap + 2 * np.sum(
        [
            rf_line.cell.settings[key]
            for key in ("tt", "th")
            if key in rf_line.cell.settings
        ]
    )

    GS_separation = rf_pad_start_width * gap_eff / rf_central_conductor_width

    sbend_large_v_offset = (
        0.5 * rf_pad_start_width
        + 0.5 * GS_separation
        - 0.5 * splitter1.settings["port_ratio"] * splitter1.settings["width_mmi"]
    )

    sbend_small_straight_length = rf_pad_length_straight * 0.5

    lbend_combiner_reff = (
        0.5 * rf_pad_start_width
        + lbend_tune_arm_reff
        + 0.5 * GS_separation
        - 0.5 * splitter2.settings["port_ratio"] * splitter2.settings["width_mmi"]
    )

    sbend_large_size = (
        sbend_large_AR * sbend_large_v_offset,
        sbend_large_v_offset,
    )
    sbend_small_size = (
        rf_pad_length_straight
        + rf_pad_length_tapered
        - 2 * sbend_small_straight_length,
        -0.5
        * (
            rf_pad_start_width
            - rf_central_conductor_width
            + GS_separation
            - gap_eff
        ),
    )
    sbend_small_straight_extend = sbend_small_straight_length
    lbend_tune_arm_reff = lbend_tune_arm_reff
    lbend_combiner_reff = lbend_combiner_reff
    bias_tuning_section_length = bias_tuning_section_length


    # placing the waveguide components from "_mzm_interferometer" cell manually

    sbend_large = lnoi400.cells.S_bend_vert(
        v_offset=sbend_large_size[1], h_extent=sbend_large_size[0], dx_straight=5.0
    )

    sbend_small = lnoi400.cells.S_bend_vert(
        v_offset=sbend_small_size[1],
        h_extent=sbend_small_size[0],
        dx_straight=sbend_small_straight_extend,
    )

    interferometer = gf.Component()

    def branch_top():
        bt = gf.Component()
        sbend_1 = bt << sbend_large
        sbend_2 = bt << sbend_small
        pm = bt << lnoi400.cells.eo_phase_shifter_high_speed(
            rib_core_width_modulator=rib_core_width_modulator,
            modulation_length=modulation_length,
            taper_length=taper_length,
            draw_cpw=False,
        )
        sbend_3 = bt << sbend_small
        sbend_2.connect("o1", sbend_1.ports["o2"])
        pm.connect("o1", sbend_2.ports["o2"])
        sbend_3.dmirror_x()
        sbend_3.connect("o1", pm.ports["o2"])

        for name, port in [
            ("o1", sbend_1.ports["o1"]),
            ("o2", sbend_3.ports["o2"]),
            ("taper_start", pm.ports["o1"]),
        ]:
            bt.add_port(name=name, port=port)
        bt.flatten()

        return bt

    def branch_tune_short(straight_unbalance: float = 0.0):
        arm = gf.Component()
        lbend = lnoi400.cells.L_turn_bend(radius=lbend_tune_arm_reff)
        straight_y = gf.components.straight(
            length=20.0 + straight_unbalance, cross_section="xs_rwg1000"
        )
        straight_x = gf.components.straight(
            length=bias_tuning_section_length, cross_section="xs_rwg1000"
        )
        symbol_to_component = {
            "b": (lbend, "o1", "o2"),
            "L": (straight_y, "o1", "o2"),
            "B": (lbend, "o2", "o1"),
            "_": (straight_x, "o1", "o2"),
        }
        sequence = "bLB_!b!L"
        arm = gf.components.component_sequence(
            sequence=sequence,
            ports_map={"phase_tuning_segment_start": ("_1", "o1")},
            symbol_to_component=symbol_to_component,
        )

        arm.add_port(port=arm.ports["phase_tuning_segment_start"])
        arm.flatten()
        return arm

    def branch_tune_long(straight_unbalance):
        return partial(branch_tune_short, straight_unbalance=straight_unbalance)()
    

    #forcing the option for a 1x2 splitter on the input and a 2x2 splitter on the output
    #splt = gf.get_component(splitter2)
    splt1 = gf.get_component(splitter1)
    splt2 = gf.get_component(splitter2)

    # Uniformly handle the cases of a 1x2 or 2x2 MMI

    out_top = splt1.ports["o2"]
    out_bottom = splt1.ports["o3"]

    # at output
    out_top_out = splt2.ports["o3"]
    out_bottom_out = splt2.ports["o4"]


    def combiner_section():
        comb_section = gf.Component()
        lbend_combiner = lnoi400.cells.L_turn_bend(radius=lbend_combiner_reff)
        lbend_top = comb_section << lbend_combiner
        lbend_bottom = comb_section << lbend_combiner
        lbend_bottom.dmirror_y()

        #pushes splitter2 to design
        combiner = comb_section << splt2
        #combiner = comb_section << splt
        lbend_top.connect("o1", out_top_out)
        lbend_bottom.connect("o1", out_bottom_out)

        # comb_section.flatten()

        exposed_ports = [
            ("o2", lbend_top.ports["o2"]),
            ("o1", combiner.ports["o1"]),
            ("o3", lbend_bottom.ports["o2"]),
        ]


        for name, port in exposed_ports:
            comb_section.add_port(name=name, port=port)

        return comb_section

    # pushes splitter1 to design
    splt_ref = interferometer << splt1
    bt = interferometer << branch_top()
    bb = interferometer << branch_top()
    bs = interferometer << branch_tune_short()
    bl = interferometer << branch_tune_long(abs(0.5 * length_imbalance))
    cs = interferometer << combiner_section()
    bb.dmirror_y()
    bt.connect("o1", out_top)
    bb.connect("o1", out_bottom)
    if length_imbalance >= 0:
        bs.dmirror_y()
        bs.connect("o1", bb.ports["o2"])
        bl.connect("o1", bt.ports["o2"])
    else:
        bs.connect("o1", bt.ports["o2"])
        bl.dmirror_y()
        bl.connect("o1", bb.ports["o2"])
    cs.dmirror_x()
    [
        cs.connect("o2", bl.ports["o2"])
        if length_imbalance >= 0
        else cs.connect("o2", bs.ports["o2"])
    ]

    exposed_ports = [
        ("o1", splt_ref.ports["o1"]),
        ("upper_taper_start", bt.ports["taper_start"]),
        ("short_bias_branch_start", bs.ports["phase_tuning_segment_start"]),
        ("long_bias_branch_start", bl.ports["phase_tuning_segment_start"]),
        ("o2", cs.ports["o1"]),
        ("o3", cs.ports["o2"]),
    ]

    for name, port in exposed_ports:
        interferometer.add_port(name=name, port=port)

    interferometer.flatten()

    #print(interferometer.get_ports_list())

    interferometer = mzm << interferometer


    interferometer.dmove(
    interferometer.ports["upper_taper_start"].dcenter,
    (0.0, 0.5 * (rf_central_conductor_width + gap_eff)),
    )



    if with_heater:
        ht_ref = mzm << lnoi400.cells.heater_straight_single(
            length=bias_tuning_section_length,
            width=heater_width,
            offset=heater_offset,
            pad_size=heater_pad_size,
        )

        if length_imbalance < 0.0:
            heater_disp = [0, 0.5 * heater_width + heater_offset]
        else:
            ht_ref.dmirror_y()
            heater_disp = [0, -0.5 * heater_width - heater_offset]

        ht_ref.dmove(
            origin=ht_ref.ports["ht_start"].dcenter,
            destination=(
                np.array(interferometer.ports["long_bias_branch_start"].dcenter)
                + heater_disp
            ),
        )

    # Expose the ports

    exposed_ports = [
        ("e1", rf_line.ports["bp1"]),
        ("e2", rf_line.ports["bp2"]),
    ]

    if with_heater:
        exposed_ports += [
            ("e3", ht_ref.ports["e1"]),
            (
                "e4",
                ht_ref.ports["e2"],
            ),
        ]

    [mzm.add_port(name=name, port=port) for name, port in exposed_ports]

    
    return mzm


#####################
# Race track resonator, FSR=30GHz
#####################
@gf.cell
def racetrack_30GHzFSR():

    #define constants for race track
    h_racetrack = 200.0
    length = 1800.0

    #define subcomponents
    u_bend_racetrack = lnoi400.cells.U_bend_racetrack(
        v_offset = h_racetrack,
        p = 1.0,
        with_arc_floorplan = True,
        cross_section = "xs_rwg3000",
    )

    #length_check = u_bend_racetrack.info['length']
    #print(length_check)   

    dc_wg = gf.components.straight(
        length = length,
        cross_section="xs_rwg3000",
    )

    def racetrack():
        # push subcomponents to design
        race_track = gf.Component()
        u_bend_ref1 = race_track << u_bend_racetrack
        u_bend_ref2 = race_track << u_bend_racetrack
        straight_ref1 = race_track << dc_wg
        straight_ref2 = race_track << dc_wg

        u_bend_ref1.connect("o2", straight_ref1.ports["o2"])
        straight_ref2.connect("o2", u_bend_ref1.ports["o1"])
        u_bend_ref2.connect("o1", straight_ref1.ports["o1"])
        u_bend_ref2.connect("o2", straight_ref2.ports["o1"])

        #race_track.flatten()

        return race_track

    # create assembly
    c = gf.Component()
    c << racetrack()

    return c

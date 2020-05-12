# -*- coding: utf-8 -*-
# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 - Suraj <dadralj18@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

__title__ = "Bill Of Material SVG"
__author__ = "Suraj"
__url__ = "https://www.freecadweb.org"


from xml.etree import ElementTree
from xml.dom import minidom

import FreeCAD

from .BOMfunc import (
    getMarkReinforcementsDict,
    getUniqueDiameterList,
    getRebarSharpEdgedLength,
    getBOMScalingFactor,
)
from .BillOfMaterialContent import makeBOMObject
from .config import *


def getColumnOffset(column_headers, diameter_list, column_header, column_width):
    """getColumnOffset(ColumnHeadersConfig, DiameterList, ColumnHeader,
    ColumnWidth):
    column_headers is a dictionary with keys: "Mark", "RebarsCount", "Diameter",
    "RebarLength", "RebarsTotalLength" and values are tuple of column_header and
    its sequence number.
    e.g. {
            "Mark": ("Mark", 1),
            "RebarsCount": ("No. of Rebars", 2),
            "Diameter": ("Diameter in mm", 3),
            "RebarLength": ("Length in m/piece", 4),
            "RebarsTotalLength": ("Total Length in m", 5),
        }

    column_header is the key from dictionary column_headers for which we need to
    find its left offset in SVG.
    column_width is the width of each column in svg.

    Returns left offset of column in svg.
    """
    seq = column_headers[column_header][1]
    if "RebarsTotalLength" in column_headers:
        if column_headers["RebarsTotalLength"][1] < seq:
            if len(diameter_list) != 0:
                seq += len(diameter_list) - 1
    offset = column_width * (seq - 1)
    return offset


def getSVGRootElement():
    """Returns svg tag element with freecad namespace."""
    svg = ElementTree.Element("svg")
    svg.set("version", "1.1")
    svg.set("xmlns", "http://www.w3.org/2000/svg")
    svg.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
    svg.set(
        "xmlns:freecad",
        "http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace",
    )
    return svg


def getSVGTextElement(
    data,
    x_offset,
    y_offset,
    font_family,
    font_size,
    text_anchor="start",
    dominant_baseline="baseline",
):
    """getSVGTextElement(Data, XOffset, YOffset, FontFamily, FontSize,
    TextAnchor, DominantBaseline):
    Returns text element with filled data and required placement.
    """
    text = ElementTree.Element(
        "text", x=str(x_offset), y=str(y_offset), style="", fill="#000000"
    )
    text.set("font-family", font_family)
    text.set("font-size", str(font_size))
    text.set("text-anchor", text_anchor)
    text.set("dominant-baseline", dominant_baseline)
    text.text = str(data)
    return text


def getSVGRectangle(x_offset, y_offset, width, height):
    """getSVGRectangle(XOffset, YOffset, RectangleWidth, RectangleHeight):
    Returns rectangle element with required placement and size of rectangle.
    """
    rectangle_svg = ElementTree.Element(
        "rect",
        x=str(x_offset),
        y=str(y_offset),
        width=str(width),
        height=str(height),
        style="fill:none;stroke-width:0.35;stroke:#000000;",
    )
    return rectangle_svg


def getSVGDataCell(
    data, x_offset, y_offset, width, height, font_family, font_size
):
    """getSVGDataCell(Data, XOffset, YOffset, CellWidth, CellHeight, FontFamily,
    FontSize):
    Returns element with rectangular cell with filled data and required
    pleacement of cell.
    """
    cell_svg = ElementTree.Element("g")
    cell_svg.set("id", "bom_table_cell")
    cell_svg.append(getSVGRectangle(x_offset, y_offset, width, height))
    cell_svg.append(
        getSVGTextElement(
            data,
            x_offset + width / 2,
            y_offset + height / 2,
            font_family,
            font_size,
            text_anchor="middle",
            dominant_baseline="central",
        )
    )
    return cell_svg


def getColumnHeadersSVG(
    column_headers,
    diameter_list,
    dia_precision,
    y_offset,
    column_width,
    row_height,
    font_family,
    font_size,
):
    """getColumnHeadersSVG(ColumnHeaders, DiameterList, DiameterPrecision,
    YOffset, ColumnWidth, RowHeight, FontFamily, FontSize):
    column_headers is a dictionary with keys: "Mark", "RebarsCount", "Diameter",
    "RebarLength", "RebarsTotalLength" and values are tuple of column_header and
    its sequence number.
    e.g. {
            "Mark": ("Mark", 1),
            "RebarsCount": ("No. of Rebars", 2),
            "Diameter": ("Diameter in mm", 3),
            "RebarLength": ("Length in m/piece", 4),
            "RebarsTotalLength": ("Total Length in m", 5),
        }

    Returns svg code for column headers.
    """
    # Delete hidden headers
    column_headers = {
        column_header: column_header_tuple
        for column_header, column_header_tuple in column_headers.items()
        if column_header_tuple[1] != 0
    }

    column_headers_svg = ElementTree.Element("g")
    column_headers_svg.set("id", "BOM_column_headers")
    column_offset = 0
    if "RebarsTotalLength" in column_headers:
        height = 2 * row_height
    else:
        height = row_height

    for column_header in sorted(
        column_headers, key=lambda x: column_headers[x][1]
    ):
        if column_header != "RebarsTotalLength":
            column_headers_svg.append(
                getSVGDataCell(
                    column_headers[column_header][0],
                    column_offset,
                    y_offset,
                    column_width,
                    height,
                    font_family,
                    font_size,
                )
            )
            column_offset += column_width
        elif column_header == "RebarsTotalLength":
            column_headers_svg.append(
                getSVGDataCell(
                    column_headers[column_header][0],
                    column_offset,
                    y_offset,
                    column_width * len(diameter_list),
                    row_height,
                    font_family,
                    font_size,
                )
            )
            dia_headers_svg = ElementTree.Element("g")
            dia_headers_svg.set("id", "BOM_headers_diameter")
            for dia in diameter_list:
                dia_headers_svg.append(
                    getSVGDataCell(
                        "#"
                        + str(round(dia.Value, dia_precision))
                        .rstrip("0")
                        .rstrip("."),
                        column_offset,
                        y_offset + row_height,
                        column_width,
                        row_height,
                        font_family,
                        font_size,
                    )
                )
                column_offset += column_width
            column_headers_svg.append(dia_headers_svg)

    return column_headers_svg


def makeBillOfMaterialSVG(
    column_headers=COLUMN_HEADERS,
    column_units=COLUMN_UNITS,
    rebar_length_type=REBAR_LENGTH_TYPE,
    font_family=FONT_FAMILY,
    font_size=FONT_SIZE,
    column_width=COLUMN_WIDTH,
    row_height=ROW_HEIGHT,
    bom_left_offset=BOM_SVG_LEFT_OFFSET,
    bom_top_offset=BOM_SVG_TOP_OFFSET,
    bom_min_right_offset=BOM_SVG_MIN_RIGHT_OFFSET,
    bom_min_bottom_offset=BOM_SVG_MIN_BOTTOM_OFFSET,
    bom_table_svg_max_width=BOM_TABLE_SVG_MAX_WIDTH,
    bom_table_svg_max_height=BOM_TABLE_SVG_MAX_HEIGHT,
    template_file=TEMPLATE_FILE,
    output_file=None,
):
    """makeBillOfMaterialSVG(ColumnHeaders, ColumnUnits, RebarLengthType,
    FontFamily, FontSize, ColumnWidth, RowHeight, BOMLeftOffset, BOMTopOffset,
    BOMMinRightOffset, BOMMinBottomOffset, BOMTableSVGMaxWidth,
    BOMTableSVGMaxHeight, TemplateFile, OutputFile):
    Generates the Rebars Material Bill SVG.

    column_headers is a dictionary with keys: "Mark", "RebarsCount", "Diameter",
    "RebarLength", "RebarsTotalLength" and values are tuple of column_header and
    its sequence number.
    e.g. {
            "Mark": ("Mark", 1),
            "RebarsCount": ("No. of Rebars", 2),
            "Diameter": ("Diameter in mm", 3),
            "RebarLength": ("Length in m/piece", 4),
            "RebarsTotalLength": ("Total Length in m", 5),
        }
    set column sequence number to 0 to hide column.

    column_units is a dictionary with keys: "Diameter", "RebarLength",
    "RebarsTotalLength" and their corresponding units as value.
    e.g. {
            "Diameter": "mm",
            "RebarLength": "m",
            "RebarsTotalLength": "m",
         }

    dia_weight_map is a dictionary with diameter as key and corresponding weight
    (kg/m) as value.
    e.g. {
            6: FreeCAD.Units.Quantity("0.222 kg/m"),
            8: FreeCAD.Units.Quantity("0.395 kg/m"),
            10: FreeCAD.Units.Quantity("0.617 kg/m"),
            12: FreeCAD.Units.Quantity("0.888 kg/m"),
            ...,
         }

    rebar_length_type can be "RealLength" or "LengthWithSharpEdges".

    Returns Bill Of Material svg code.
    """
    mark_reinforcements_dict = getMarkReinforcementsDict()
    diameter_list = getUniqueDiameterList(mark_reinforcements_dict)

    svg = getSVGRootElement()

    # Get user preferred unit precision
    precision = FreeCAD.ParamGet(
        "User parameter:BaseApp/Preferences/Units"
    ).GetInt("Decimals")

    bom_table_svg = ElementTree.Element("g")
    bom_table_svg.set("id", "BOM_table")

    y_offset = 0
    column_headers_svg = getColumnHeadersSVG(
        column_headers,
        diameter_list,
        precision,
        y_offset,
        column_width,
        row_height,
        font_family,
        font_size,
    )
    bom_table_svg.append(column_headers_svg)

    # Dictionary to store total length of rebars corresponding to its dia
    dia_total_length_dict = {
        dia.Value: FreeCAD.Units.Quantity("0 mm") for dia in diameter_list
    }

    if "RebarsTotalLength" in column_headers:
        first_row = 3
        current_row = 3
        y_offset += 2 * row_height
    else:
        first_row = 2
        current_row = 2
        y_offset += row_height

    for mark_number in sorted(mark_reinforcements_dict):
        base_rebar = mark_reinforcements_dict[mark_number][0].BaseRebar
        bom_row_svg = ElementTree.Element("g")
        # TODO: Modify logic of str(current_row - first_row + 1)
        # first_row variable maybe eliminated
        bom_row_svg.set(
            "id", "BOM_table_row" + str(current_row - first_row + 1)
        )

        if "Mark" in column_headers:
            column_offset = getColumnOffset(
                column_headers, diameter_list, "Mark", column_width
            )
            bom_row_svg.append(
                getSVGDataCell(
                    mark_number,
                    column_offset,
                    y_offset,
                    column_width,
                    row_height,
                    font_family,
                    font_size,
                )
            )

        rebars_count = 0
        for reinforcement in mark_reinforcements_dict[mark_number]:
            rebars_count += reinforcement.Amount

        if "RebarsCount" in column_headers:
            column_offset = getColumnOffset(
                column_headers, diameter_list, "RebarsCount", column_width
            )
            bom_row_svg.append(
                getSVGDataCell(
                    rebars_count,
                    column_offset,
                    y_offset,
                    column_width,
                    row_height,
                    font_family,
                    font_size,
                )
            )

        if "Diameter" in column_headers:
            disp_diameter = base_rebar.Diameter
            if "Diameter" in column_units:
                disp_diameter = (
                    str(
                        round(
                            disp_diameter.getValueAs(
                                column_units["Diameter"]
                            ).Value,
                            precision,
                        )
                    )
                    .rstrip("0")
                    .rstrip(".")
                    + " "
                    + column_units["Diameter"]
                )
            else:
                disp_diameter = str(round(disp_diameter, precision))
            column_offset = getColumnOffset(
                column_headers, diameter_list, "Diameter", column_width
            )
            bom_row_svg.append(
                getSVGDataCell(
                    disp_diameter,
                    column_offset,
                    y_offset,
                    column_width,
                    row_height,
                    font_family,
                    font_size,
                )
            )

        base_rebar_length = FreeCAD.Units.Quantity("0 mm")
        if "RebarLength" in column_headers:
            if rebar_length_type == "RealLength":
                base_rebar_length = base_rebar.Length
            else:
                base_rebar_length = getRebarSharpEdgedLength(base_rebar)
            disp_base_rebar_length = base_rebar_length
            if "RebarLength" in column_units:
                disp_base_rebar_length = (
                    str(
                        round(
                            base_rebar_length.getValueAs(
                                column_units["RebarLength"]
                            ).Value,
                            precision,
                        )
                    )
                    .rstrip("0")
                    .rstrip(".")
                    + " "
                    + column_units["RebarLength"]
                )
            else:
                disp_base_rebar_length = str(
                    round(disp_base_rebar_length, precision)
                )

            column_offset = getColumnOffset(
                column_headers, diameter_list, "RebarLength", column_width
            )
            bom_row_svg.append(
                getSVGDataCell(
                    disp_base_rebar_length,
                    column_offset,
                    y_offset,
                    column_width,
                    row_height,
                    font_family,
                    font_size,
                )
            )

        rebar_total_length = FreeCAD.Units.Quantity("0 mm")
        for reinforcement in mark_reinforcements_dict[mark_number]:
            rebar_total_length += reinforcement.Amount * base_rebar_length
        dia_total_length_dict[base_rebar.Diameter.Value] += rebar_total_length

        if "RebarsTotalLength" in column_headers:
            disp_rebar_total_length = rebar_total_length
            if "RebarsTotalLength" in column_units:
                disp_rebar_total_length = (
                    str(
                        round(
                            rebar_total_length.getValueAs(
                                column_units["RebarsTotalLength"]
                            ).Value,
                            precision,
                        )
                    )
                    .rstrip("0")
                    .rstrip(".")
                    + " "
                    + column_units["RebarsTotalLength"]
                )
            else:
                disp_rebar_total_length = str(
                    round(disp_rebar_total_length, precision)
                )

            column_offset = getColumnOffset(
                column_headers, diameter_list, "RebarsTotalLength", column_width
            )
            for dia in diameter_list:
                if dia == base_rebar.Diameter:
                    bom_row_svg.append(
                        getSVGDataCell(
                            disp_rebar_total_length,
                            column_offset
                            + (diameter_list.index(dia)) * column_width,
                            y_offset,
                            column_width,
                            row_height,
                            font_family,
                            font_size,
                        )
                    )
                else:
                    bom_row_svg.append(
                        getSVGRectangle(
                            column_offset
                            + diameter_list.index(dia) * column_width,
                            y_offset,
                            column_width,
                            row_height,
                        )
                    )

        bom_table_svg.append(bom_row_svg)
        y_offset += row_height
        current_row += 1

    bom_table_svg.append(
        getSVGRectangle(
            0,
            y_offset,
            column_width * (len(column_headers) + len(diameter_list) - 1),
            row_height,
        )
    )
    y_offset += row_height

    bom_data_total_svg = ElementTree.Element("g")
    bom_data_total_svg.set("id", "BOM_data_total")
    # Display total length, weight/m and total weight of all rebars
    if "RebarsTotalLength" in column_headers:
        if column_headers["RebarsTotalLength"][1] != 1:
            rebar_total_length_offset = getColumnOffset(
                column_headers, diameter_list, "RebarsTotalLength", column_width
            )

            bom_data_total_svg.append(
                getSVGDataCell(
                    "Total length in "
                    + column_units["RebarsTotalLength"]
                    + "/Diameter",
                    0,
                    y_offset,
                    rebar_total_length_offset,
                    row_height,
                    font_family,
                    font_size,
                )
            )
            bom_data_total_svg.append(
                getSVGDataCell(
                    "Weight in Kg/" + column_units["RebarsTotalLength"],
                    0,
                    y_offset + row_height,
                    rebar_total_length_offset,
                    row_height,
                    font_family,
                    font_size,
                )
            )
            bom_data_total_svg.append(
                getSVGDataCell(
                    "Total Weight in Kg/Diameter",
                    0,
                    y_offset + 2 * row_height,
                    rebar_total_length_offset,
                    row_height,
                    font_family,
                    font_size,
                )
            )

            for i, dia in enumerate(diameter_list):
                disp_dia_total_length = dia_total_length_dict[dia.Value]
                if "RebarsTotalLength" in column_units:
                    disp_dia_total_length = (
                        str(
                            round(
                                disp_dia_total_length.getValueAs(
                                    column_units["RebarsTotalLength"]
                                ).Value,
                                precision,
                            )
                        )
                        .rstrip("0")
                        .rstrip(".")
                        + " "
                        + column_units["RebarsTotalLength"]
                    )
                else:
                    disp_dia_total_length = str(
                        round(disp_dia_total_length, precision)
                    )

                bom_data_total_svg.append(
                    getSVGDataCell(
                        disp_dia_total_length,
                        rebar_total_length_offset + i * column_width,
                        y_offset,
                        column_width,
                        row_height,
                        font_family,
                        font_size,
                    )
                )

                if dia.Value in DIA_WEIGHT_MAP:
                    disp_dia_weight = DIA_WEIGHT_MAP[dia.Value]
                    if "RebarsTotalLength" in column_units:
                        disp_dia_weight = (
                            str(
                                round(
                                    disp_dia_weight.getValueAs(
                                        "kg/"
                                        + column_units["RebarsTotalLength"]
                                    ).Value,
                                    precision,
                                )
                            )
                            .rstrip("0")
                            .rstrip(".")
                            + " "
                            + column_units["RebarsTotalLength"]
                        )
                    else:
                        disp_dia_weight = str(round(disp_dia_weight, precision))

                    bom_data_total_svg.append(
                        getSVGDataCell(
                            disp_dia_weight,
                            rebar_total_length_offset + i * column_width,
                            y_offset + row_height,
                            column_width,
                            row_height,
                            font_family,
                            font_size,
                        )
                    )
                    bom_data_total_svg.append(
                        getSVGDataCell(
                            round(
                                DIA_WEIGHT_MAP[dia.Value]
                                * dia_total_length_dict[dia.Value],
                                precision,
                            ),
                            rebar_total_length_offset + i * column_width,
                            y_offset + 2 * row_height,
                            column_width,
                            row_height,
                            font_family,
                            font_size,
                        )
                    )
                else:
                    bom_data_total_svg.append(
                        getSVGRectangle(
                            rebar_total_length_offset + i * column_width,
                            y_offset + row_height,
                            column_width,
                            row_height,
                        )
                    )
                    bom_data_total_svg.append(
                        getSVGRectangle(
                            rebar_total_length_offset + i * column_width,
                            y_offset + 2 * row_height,
                            column_width,
                            row_height,
                        )
                    )

            for remColumn in range(
                len(column_headers) - column_headers["RebarsTotalLength"][1]
            ):
                column_offset = (
                    column_headers["RebarsTotalLength"][1]
                    + len(diameter_list)
                    - 1
                    + remColumn
                ) * column_width
                for row in range(3):
                    bom_data_total_svg.append(
                        getSVGRectangle(
                            column_offset,
                            y_offset + row * row_height,
                            column_width,
                            row_height,
                        )
                    )
        else:
            for i, dia in enumerate(diameter_list):
                disp_dia_total_length = dia_total_length_dict[dia.Value]
                if "RebarsTotalLength" in column_units:
                    disp_dia_total_length = (
                        str(
                            round(
                                disp_dia_total_length.getValueAs(
                                    column_units["RebarsTotalLength"]
                                ).Value,
                                precision,
                            )
                        )
                        .rstrip("0")
                        .rstrip(".")
                        + " "
                        + column_units["RebarsTotalLength"]
                    )
                else:
                    disp_dia_total_length = str(
                        round(disp_dia_total_length, precision)
                    )

                bom_data_total_svg.append(
                    getSVGDataCell(
                        disp_dia_total_length,
                        i * column_width,
                        y_offset,
                        column_width,
                        row_height,
                        font_family,
                        font_size,
                    )
                )

                if dia.Value in DIA_WEIGHT_MAP:
                    disp_dia_weight = DIA_WEIGHT_MAP[dia.Value]
                    if "RebarsTotalLength" in column_units:
                        disp_dia_weight = (
                            str(
                                round(
                                    disp_dia_weight.getValueAs(
                                        "kg/"
                                        + column_units["RebarsTotalLength"]
                                    ).Value,
                                    precision,
                                )
                            )
                            .rstrip("0")
                            .rstrip(".")
                            + " "
                            + column_units["RebarsTotalLength"]
                        )
                    else:
                        disp_dia_weight = str(round(disp_dia_weight, precision))

                    bom_data_total_svg.append(
                        getSVGDataCell(
                            disp_dia_weight,
                            i * column_width,
                            y_offset + row_height,
                            column_width,
                            row_height,
                            font_family,
                            font_size,
                        )
                    )
                    bom_data_total_svg.append(
                        getSVGDataCell(
                            round(
                                DIA_WEIGHT_MAP[dia.Value]
                                * dia_total_length_dict[dia.Value],
                                precision,
                            ),
                            i * column_width,
                            y_offset + 2 * row_height,
                            column_width,
                            row_height,
                            font_family,
                            font_size,
                        )
                    )

            first_txt_column_offset = len(diameter_list) * column_width
            bom_data_total_svg.append(
                getSVGDataCell(
                    "Total length in "
                    + column_units["RebarsTotalLength"]
                    + "/Diameter",
                    first_txt_column_offset,
                    y_offset,
                    column_width * (len(column_headers) - 1),
                    row_height,
                    font_family,
                    font_size,
                )
            )
            bom_data_total_svg.append(
                getSVGDataCell(
                    "Weight in Kg/" + column_units["RebarsTotalLength"],
                    first_txt_column_offset,
                    y_offset + row_height,
                    column_width * (len(column_headers) - 1),
                    row_height,
                    font_family,
                    font_size,
                )
            )
            bom_data_total_svg.append(
                getSVGDataCell(
                    "Total Weight in Kg/Diameter",
                    first_txt_column_offset,
                    y_offset + 2 * row_height,
                    column_width * (len(column_headers) - 1),
                    row_height,
                    font_family,
                    font_size,
                )
            )
    y_offset += 3 * row_height
    bom_table_svg.append(bom_data_total_svg)
    svg.append(bom_table_svg)

    bom_height = y_offset
    bom_width = column_width * (len(column_headers) + len(diameter_list) - 1)
    svg.set("width", str(bom_width) + "mm")
    svg.set("height", str(bom_height) + "mm")
    svg.set("viewBox", "0 0 {} {}".format(bom_width, bom_height))
    svg_output = minidom.parseString(
        ElementTree.tostring(svg, encoding="unicode")
    ).toprettyxml(indent="  ")

    bom_obj = makeBOMObject(template_file)
    template_height = bom_obj.Template.Height.Value
    template_width = bom_obj.Template.Width.Value

    scaling_factor = getBOMScalingFactor(
        bom_width,
        bom_height,
        bom_left_offset,
        bom_top_offset,
        template_width,
        template_height,
        bom_min_right_offset,
        bom_min_bottom_offset,
        bom_table_svg_max_width,
        bom_table_svg_max_height,
    )

    bom_content_obj = bom_obj.Views[0]
    bom_content_obj.Symbol = svg_output
    bom_content_obj.Font = font_family
    bom_content_obj.FontSize = font_size
    bom_content_obj.Template = bom_obj.Template
    bom_content_obj.Width = bom_width
    bom_content_obj.Height = bom_height
    bom_content_obj.LeftOffset = bom_left_offset
    bom_content_obj.TopOffset = bom_top_offset
    bom_content_obj.MinRightOffset = bom_min_right_offset
    bom_content_obj.MinBottomOffset = bom_min_bottom_offset
    bom_content_obj.MaxWidth = bom_table_svg_max_width
    bom_content_obj.MaxHeight = bom_table_svg_max_height
    bom_content_obj.X = bom_width * scaling_factor / 2 + bom_left_offset
    bom_content_obj.Y = (
        template_height - bom_height * scaling_factor / 2 - bom_top_offset
    )
    bom_content_obj.Scale = scaling_factor

    template_svg = ""
    try:
        with open(template_file, "r") as template:
            template_svg = template.read()
    except:
        pass
        FreeCAD.Console.PrintError(
            "Error reading template file " + str(template_file) + "\n"
        )

    if output_file:
        svg_sheet = minidom.parseString(
            ElementTree.tostring(bom_table_svg, encoding="unicode")
        ).toprettyxml(indent="  ")

        if template_svg:
            bom_table_svg.set(
                "transform",
                "translate({} {}) scale({})".format(
                    bom_left_offset, bom_top_offset, scaling_factor
                ),
            )
            bom_svg = minidom.parseString(
                ElementTree.tostring(bom_table_svg, encoding="unicode")
            ).toprettyxml(indent="  ")
            # Remove xml declaration as XML declaration allowed only at the
            # start of the document
            if "<?xml" in bom_svg.splitlines()[0]:
                bom_svg = bom_svg.lstrip(bom_svg.splitlines()[0])
            svg_sheet = template_svg.replace("<!-- DrawingContent -->", bom_svg)

        try:
            with open(output_file, "w") as svg_output_file:
                svg_output_file.write(svg_sheet)
        except:
            FreeCAD.Console.PrintError(
                "Error writing svg to file " + str(svg_output_file) + "\n"
            )

    FreeCAD.ActiveDocument.recompute()
    return svg_output

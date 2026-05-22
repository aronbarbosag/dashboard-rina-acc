import altair as alt

from app.config import CHART_HEIGHT, CHART_TEAL


def chart_config(chart):
    return (
        chart.configure_view(strokeWidth=0, fill="#ffffff")
        .configure(
            background="#ffffff",
            font="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        )
        .configure_axis(
            gridColor="#EEF2F7",
            gridDash=[2, 3],
            labelColor="#94A3B8",
            titleColor=CHART_TEAL,
            domainColor="#E5EBF3",
            tickColor="#E5EBF3",
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight=600,
            titlePadding=10,
        )
        .configure_legend(
            labelColor=CHART_TEAL,
            titleColor=CHART_TEAL,
            labelFontSize=11,
            titleFontSize=11,
        )
    )


def make_bar_chart(
    dataframe, x, y, tooltip, height=CHART_HEIGHT, sort="-x", color=CHART_TEAL
):
    if dataframe.empty:
        return None

    base = alt.Chart(dataframe).encode(
        x=alt.X(x, sort=sort, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=None),
        tooltip=tooltip,
    )
    bars = base.mark_bar(
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color=color,
    )
    labels = base.mark_text(
        dy=-6,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(y, format=",.0f"),
    )
    chart = (bars + labels).properties(height=height)
    return chart_config(chart)


def make_horizontal_bar(
    dataframe,
    y,
    x,
    tooltip,
    height=CHART_HEIGHT,
    color=CHART_TEAL,
    value_format=",.0f",
):
    if dataframe.empty:
        return None

    base = alt.Chart(dataframe).encode(
        y=alt.Y(y, sort="-x", title=None),
        x=alt.X(x, title=None),
        tooltip=tooltip,
    )
    bars = base.mark_bar(
        cornerRadiusTopRight=5,
        cornerRadiusBottomRight=5,
        color=color,
    )
    labels = base.mark_text(
        align="left",
        dx=6,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(x, format=value_format),
    )
    chart = (bars + labels).properties(height=height)
    return chart_config(chart)


def make_area_line_chart(
    dataframe, x, y, tooltip, sort, color=CHART_TEAL, height=CHART_HEIGHT
):
    if dataframe.empty:
        return None

    start = color
    base = alt.Chart(dataframe).encode(
        x=alt.X(x, sort=sort, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=None),
        tooltip=tooltip,
    )

    area = base.mark_area(
        color=start,
        opacity=0.12,
    )
    line = base.mark_line(strokeWidth=3, color=start)
    points = base.mark_point(size=80, fill=start, stroke="#ffffff", strokeWidth=2)
    labels = base.mark_text(
        dy=-10,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(y, format=".2f"),
    )

    return chart_config((area + line + points + labels).properties(height=height))

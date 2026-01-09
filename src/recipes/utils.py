from io import BytesIO
import base64
import matplotlib.pyplot as plt

# Predefined color schemes
COLOR_SCHEMES = {
    "default": {
        "bar_colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"],
        "pie_colors": {"Easy": "#90EE90", "Medium": "#FFD700", "Intermediate": "#FF8C00", "Hard": "#FF4500"},
        "line_color": "#2E86AB",
        "marker_color": "#A23B72",
    },
    "pastel": {
        "bar_colors": ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E1BAFF", "#FFBAE1"],
        "pie_colors": {"Easy": "#B8E6B8", "Medium": "#FFE4B5", "Intermediate": "#FFB5B5", "Hard": "#D4A5FF"},
        "line_color": "#87CEEB",
        "marker_color": "#DDA0DD",
    },
    "brand": {
        "bar_colors": ["#f37f20", "#6fc3aa", "#a9c57c", "#c0a659", "#d7b25b"],
        "pie_colors": {"Easy": "#c0a659", "Medium": "#a9c57c", "Intermediate": "#6fc3aa", "Hard": "#f37f20"},
        "line_color": "#f37f20",
        "marker_color": "#6fc3aa",
    },
    "monochrome": {
        "bar_colors": ["#2C3E50", "#34495E", "#7F8C8D", "#95A5A6", "#BDC3C7", "#D5DBDB", "#ECF0F1"],
        "pie_colors": {"Easy": "#27AE60", "Medium": "#F39C12", "Intermediate": "#E67E22", "Hard": "#E74C3C"},
        "line_color": "#2C3E50",
        "marker_color": "#E74C3C",
    },
}


def get_color_scheme(scheme_name="default"):
    """
    Get a predefined color scheme

    Args:
        scheme_name: Name of the color scheme ('default', 'pastel', 'brand', 'monochrome')

    Returns:
        dict: Color scheme configuration
    """
    return COLOR_SCHEMES.get(scheme_name, COLOR_SCHEMES["default"])


def get_graph():
    """Convert matplotlib plot to base64 image for HTML display"""
    # create a BytesIO buffer for the image
    buffer = BytesIO()
    # create a plot with a bytesIO object as a file-like object. Set format to png
    plt.savefig(buffer, format="png")
    # set cursor to the beginning of the stream
    buffer.seek(0)
    # retrieve the content of the file
    image_png = buffer.getvalue()
    # encode the bytes-like object
    graph = base64.b64encode(image_png)
    # decode to get the string as output
    graph = graph.decode("utf-8")
    # free up the memory of buffer
    buffer.close()
    # return the image/graph
    return graph


def get_chart(chart_type, data, **kwargs):
    """
    Generate a single chart based on recipe data

    Args:
        chart_type: Type of chart ('#1'=bar, '#2'=pie, '#3'=line)
        data: pandas DataFrame with recipe data
        **kwargs: Additional parameters like labels, color_scheme
    """
    # switch plot backend to AGG (Anti-Grain Geometry) - to write to file
    # AGG is preferred solution to write PNG files
    plt.switch_backend("AGG")
    # specify figure size
    plt.figure(figsize=(8, 5))

    # Get color scheme
    color_scheme = get_color_scheme(kwargs.get("color_scheme", "default"))

    # select chart_type based on user input from the form
    if chart_type == "#1":
        # Bar chart: Recipe names on x-axis, cooking time on y-axis
        # Color customization options
        colors = kwargs.get("colors", color_scheme["bar_colors"])

        plt.bar(data["name"], data["cooking_time"], color=colors[: len(data)])
        plt.title("Recipe Cooking Times")
        plt.xlabel("Recipe Name")
        plt.ylabel("Cooking Time (minutes)")
        plt.xticks(rotation=45, ha="right")

    elif chart_type == "#2":
        # Pie chart: Distribution of difficulty levels
        difficulty_counts = data["difficulty"].value_counts()

        # Color customization for pie chart
        colors = kwargs.get("colors", None)
        if colors is None:
            colors = [color_scheme["pie_colors"].get(level, "#CCCCCC") for level in difficulty_counts.index]

        plt.pie(difficulty_counts.values, labels=difficulty_counts.index, autopct="%1.1f%%", colors=colors)
        plt.title("Recipe Difficulty Distribution")

    elif chart_type == "#3":
        # Line chart: Cooking time vs ingredient count
        # Color customization for line chart
        line_color = kwargs.get("color", color_scheme["line_color"])
        marker_color = kwargs.get("marker_color", color_scheme["marker_color"])

        plt.plot(
            data["ingredient_count"],
            data["cooking_time"],
            marker="o",
            color=line_color,
            markerfacecolor=marker_color,
            markeredgecolor="white",
            markeredgewidth=2,
            linewidth=3,
        )
        plt.title("Cooking Time vs Number of Ingredients")
        plt.xlabel("Number of Ingredients")
        plt.ylabel("Cooking Time (minutes)")

    else:
        print("unknown chart type")

    # specify layout details
    plt.tight_layout()
    # render the graph to file
    chart = get_graph()
    return chart


def get_all_charts(data, **kwargs):
    """
    Generate all three chart types based on recipe data

    Args:
        data: pandas DataFrame with recipe data
        **kwargs: Additional parameters like labels, color_scheme

    Returns:
        dict: Dictionary containing all three charts with their types as keys
    """
    charts = {}

    # Generate bar chart
    charts["bar"] = get_chart("#1", data, **kwargs)

    # Generate pie chart
    charts["pie"] = get_chart("#2", data, **kwargs)

    # Generate line chart
    charts["line"] = get_chart("#3", data, **kwargs)

    return charts


def get_chart_with_colors(chart_type, data, color_scheme="default", custom_colors=None):
    """
    Generate a chart with specific color customization

    Args:
        chart_type: Type of chart ('#1'=bar, '#2'=pie, '#3'=line)
        data: pandas DataFrame with recipe data
        color_scheme: Predefined color scheme name ('default', 'pastel', 'vibrant', 'monochrome')
        custom_colors: Dict with custom colors to override scheme

    Returns:
        base64 encoded chart image
    """
    kwargs = {"color_scheme": color_scheme}

    # Override with custom colors if provided
    if custom_colors:
        kwargs.update(custom_colors)

    return get_chart(chart_type, data, **kwargs)

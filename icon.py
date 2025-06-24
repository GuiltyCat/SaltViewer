import svgwrite


def main():
    size = 100
    dwg = svgwrite.Drawing("icon.svg", size=(size, size))
    white = False
    width = 20
    for i in range(0, 101, width):
        color = "white" if white else "black"
        dwg.add(dwg.rect((i / 2, i / 2), (size - i, size - i), fill=color))
        white = not white

    line_width = width / 4
    dwg.add(dwg.line((0, 0), (size, size), stroke="black", stroke_width=line_width))
    dwg.add(
        dwg.line(
            (size, 0),
            (size - width * 2, width * 2),
            stroke="white",
            stroke_width=line_width,
        )
    )
    dwg.add(
        dwg.line(
            (size - size + width * 2, size - width * 2),
            (0, size),
            stroke="white",
            stroke_width=line_width,
        )
    )
    dwg.save()


if __name__ == "__main__":
    main()

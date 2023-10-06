const rectangle = document.createElement("div");
rectangle.style.position = "absolute";
rectangle.style.backgroundColor = "rgba(255,255,0, 0.1)";
rectangle.style.border = "0px dashed black";
document.body.appendChild(rectangle);

    let rec_top = 0;
    let rec_height = 15;
    let rec_left = 0;
    let rec_width = 15;

    let isDragged = false;
    let rectangleCoords = [];

    const clearRectangleCoords = () => {
        rectangleCoords = [];
    };

    const addFirstRectangleCoords = coords => {
        rectangleCoords[0] = coords;
    };

    const addSecondRectangleCoords = coords => {
        rectangleCoords[1] = coords;
    };

    const redrawRectangle = () => {
        const top = Math.min(rectangleCoords[0].y, rectangleCoords[1].y);
        const height = Math.max(rectangleCoords[0].y, rectangleCoords[1].y) - top;
        const left = Math.min(rectangleCoords[0].x, rectangleCoords[1].x);
        const width = Math.max(rectangleCoords[0].x, rectangleCoords[1].x) - left;

        rec_top = top;
        rec_height = height;
        rec_width = width;
        rec_left = left;

      rectangle.style.top = top + "px";
      rectangle.style.height = height + "px";
      rectangle.style.left = left + "px";
      rectangle.style.width = width + "px";
    };

    window.addEventListener("mousedown", e => {
        isDragged = true;
      clearRectangleCoords();

      rec_top = e.pageY
      rec_left = e.pageX

      addFirstRectangleCoords({x: e.pageX, y: e.pageY});
      addSecondRectangleCoords({x: e.pageX, y: e.pageY});
      redrawRectangle();
    });

    window.addEventListener("mousemove", e => {
        if (isDragged) {
        addSecondRectangleCoords({x: e.pageX, y: e.pageY});
        redrawRectangle();

        var contentHolder = document.getElementById('coord');
        contentHolder.innerHTML = [rec_width, rec_height];
      }
    });

    window.addEventListener("mouseup", e => {
        if (isDragged) {
        addSecondRectangleCoords({x: e.pageX, y: e.pageY});
        redrawRectangle();
        isDragged = false;

        rec_width = e.pageX - rec_left
        rec.height = e.pageY - rec_top
      }
    });



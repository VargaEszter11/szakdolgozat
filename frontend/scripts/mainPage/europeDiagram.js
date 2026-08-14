import { escapeHtml, t } from './helpers.js';
import { getEuropeTotal } from './europe.js';

function piePoint(cx, cy, r, angleDeg) {
  var rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: +(cx + r * Math.cos(rad)).toFixed(2),
    y: +(cy + r * Math.sin(rad)).toFixed(2)
  };
}

function pieSlice(cx, cy, r, startDeg, endDeg) {
  if (endDeg - startDeg >= 359.999) {
    return (
      'M' +
      cx +
      ' ' +
      cy +
      ' m-' +
      r +
      ',0 a' +
      r +
      ',' +
      r +
      ' 0 1,1 ' +
      r * 2 +
      ',0 a' +
      r +
      ',' +
      r +
      ' 0 1,1 -' +
      r * 2 +
      ',0'
    );
  }
  var start = piePoint(cx, cy, r, startDeg);
  var end = piePoint(cx, cy, r, endDeg);
  var large = endDeg - startDeg > 180 ? 1 : 0;
  return (
    'M' +
    cx +
    ' ' +
    cy +
    ' L' +
    start.x +
    ' ' +
    start.y +
    ' A' +
    r +
    ' ' +
    r +
    ' 0 ' +
    large +
    ' 1 ' +
    end.x +
    ' ' +
    end.y +
    ' Z'
  );
}

export function renderDiagram(visitedCount, visitedRatio, chartAria) {
  var diagramEl = document.getElementById('mainEuropeDiagram');
  if (!diagramEl) return;

  var europeTotal = getEuropeTotal();
  var centerLabel = visitedCount + ' / ' + europeTotal;
  var size = 160;
  var cx = size / 2;
  var cy = size / 2;
  var r = 68;
  var visitedAngle = visitedRatio * 360;
  var paths =
    '<circle class="main-europe-chart-slice main-europe-chart-slice--unvisited" cx="' +
    cx +
    '" cy="' +
    cy +
    '" r="' +
    r +
    '"></circle>';

  if (visitedCount > 0 && visitedAngle < 360) {
    paths +=
      '<path class="main-europe-chart-slice main-europe-chart-slice--visited" d="' +
      pieSlice(cx, cy, r, 0, visitedAngle) +
      '"></path>';
  } else if (visitedCount >= europeTotal && europeTotal > 0) {
    paths +=
      '<circle class="main-europe-chart-slice main-europe-chart-slice--visited" cx="' +
      cx +
      '" cy="' +
      cy +
      '" r="' +
      r +
      '"></circle>';
  }

  paths +=
    '<circle class="main-europe-chart-outline" cx="' +
    cx +
    '" cy="' +
    cy +
    '" r="' +
    r +
    '"></circle>';

  diagramEl.innerHTML =
    '<div class="main-europe-chart-pie-outer" role="img" aria-label="' +
    chartAria +
    '">' +
    '<svg class="main-europe-chart-svg" viewBox="0 0 ' +
    size +
    ' ' +
    size +
    '" aria-hidden="true">' +
    paths +
    '</svg>' +
    '<span class="main-europe-chart-center-label">' +
    centerLabel +
    '</span>' +
    '</div>' +
    '<div class="main-europe-chart-legend-key">' +
    '<span><span class="main-europe-chart-swatch main-europe-chart-swatch--visited"></span>' +
    escapeHtml(t('mainPage.europeChartVisited', 'Visited')) +
    '</span>' +
    '<span><span class="main-europe-chart-swatch main-europe-chart-swatch--unvisited"></span>' +
    escapeHtml(t('mainPage.europeChartNotVisited', 'Not visited yet')) +
    '</span>' +
    '</div>';
}

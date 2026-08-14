import { formatVisitDates } from './helpers.js';
import { resolveEuropeIso } from './europe.js';

export var DEFAULT_IMAGE =
  'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80';

export function placeImageUrl(place) {
  if (place.image) return place.image;
  if (place.photo_path) return place.photo_path;
  return DEFAULT_IMAGE;
}

export function inclusiveDays(startValue, endValue) {
  var startIso = String(startValue || '').trim().slice(0, 10);
  var endIso = String(endValue || '').trim().slice(0, 10);
  if (!startIso && !endIso) return 0;
  var a = startIso || endIso;
  var b = endIso || startIso;
  var d0 = new Date(a + 'T12:00:00');
  var d1 = new Date(b + 'T12:00:00');
  if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return 0;
  if (d1 < d0) {
    var tmp = d0;
    d0 = d1;
    d1 = tmp;
  }
  return Math.floor((d1 - d0) / 86400000) + 1;
}

export function normalizePlace(item) {
  var placeName = item.place_name || item.placeName || item.name || '';
  var country = item.country || '';
  var name =
    window.Countries && window.Countries.formatPlace
      ? window.Countries.formatPlace(placeName, country)
      : placeName + (country ? ', ' + country : '');
  if (!name.trim()) name = 'Unnamed place';

  var dateValue = item.date || item.visitedDate || item.dateVisited;
  var endDateValue = item.end_date || item.endDate || item.visitedEndDate;
  var d = dateValue ? new Date(dateValue) : null;
  var endD = endDateValue ? new Date(endDateValue) : null;
  var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
  if (endD && !isNaN(endD.getTime()) && endD.getTime() > dateSortKey) {
    dateSortKey = endD.getTime();
  }

  var europeIso = resolveEuropeIso(country);
  var image = item.image || item.photo_path || null;

  return {
    place_name: placeName,
    name: name,
    country: country,
    europeIso: europeIso,
    date: formatVisitDates(dateValue, endDateValue),
    dateSortKey: dateSortKey,
    daySpan: inclusiveDays(dateValue, endDateValue),
    description: item.description || item.notes || '',
    image: image,
    photo_path: item.photo_path || null,
    latitude: item.latitude != null ? item.latitude : null,
    longitude: item.longitude != null ? item.longitude : null
  };
}

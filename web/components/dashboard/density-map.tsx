"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl, { type Map as MaplibreMap, type MapGeoJSONFeature } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { fmt2, fmtInt } from "@/lib/format";

type TileLayer = "nuts2" | "gminy";

const THERMAL_BREAKS = [0, 0.5, 1, 2, 5, 10];
const THERMAL_COLORS = [
  "var(--map-0)",
  "var(--map-1)",
  "var(--map-2)",
  "var(--map-3)",
  "var(--map-4)",
  "var(--map-5)",
];

function readCssVar(name: string): string {
  if (typeof window === "undefined") return "#000";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function densityColorExpr(): maplibregl.ExpressionSpecification {
  // Maplibre `step` expression: returns map-0 for null/<= 0, otherwise stepped color.
  // We use the resolved colors so the map paints correctly without var() resolution.
  const colors = THERMAL_COLORS.map((v) => readCssVar(v.replace(/var\((.+)\)/, "$1")));
  return [
    "case",
    [
      "any",
      ["==", ["get", "lockers_per_10k"], null],
      ["<=", ["to-number", ["get", "lockers_per_10k"], -1], 0],
    ],
    colors[0],
    [
      "step",
      ["to-number", ["get", "lockers_per_10k"], 0],
      colors[1],
      THERMAL_BREAKS[1], colors[2],
      THERMAL_BREAKS[2], colors[3],
      THERMAL_BREAKS[3], colors[4],
      THERMAL_BREAKS[4], colors[5],
    ],
  ] as unknown as maplibregl.ExpressionSpecification;
}

export function DensityMap() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const [layer, setLayer] = useState<TileLayer>("nuts2");
  const [hover, setHover] = useState<{
    name: string;
    code: string;
    density: number | null;
    n_lockers: number;
    population: number;
    country: string;
    x: number;
    y: number;
  } | null>(null);

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
        sources: {
          carto: {
            type: "raster",
            tiles: [
              "https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png",
              "https://b.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png",
              "https://c.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png",
              "https://d.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
          },
          labels: {
            type: "raster",
            tiles: [
              "https://a.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}@2x.png",
              "https://b.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
          },
          nuts2: {
            type: "vector",
            tiles: [`${API_BASE_URL}/tiles/nuts2_density_tiles/{z}/{x}/{y}`],
            minzoom: 0,
            maxzoom: 8,
            promoteId: "code",
          },
          gminy: {
            type: "vector",
            tiles: [`${API_BASE_URL}/tiles/gminy_density_tiles/{z}/{x}/{y}`],
            minzoom: 5,
            maxzoom: 12,
            promoteId: "teryt",
          },
        },
        layers: [
          { id: "bg", type: "background", paint: { "background-color": "#0A0A0B" } },
          {
            id: "carto",
            type: "raster",
            source: "carto",
            paint: { "raster-opacity": 0.45, "raster-saturation": -0.5 },
          },
        ],
      },
      center: [19.5, 52],
      zoom: 4.2,
      attributionControl: false,
      cooperativeGestures: false,
    });

    mapRef.current = map;

    map.on("load", () => {
      // NUTS-2 fill
      map.addLayer({
        id: "nuts2-fill",
        type: "fill",
        source: "nuts2",
        "source-layer": "nuts2_density",
        paint: {
          "fill-color": densityColorExpr(),
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.92,
            0.78,
          ],
        },
      });
      map.addLayer({
        id: "nuts2-line",
        type: "line",
        source: "nuts2",
        "source-layer": "nuts2_density",
        paint: {
          "line-color": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            "#F5C04E",
            "rgba(60, 60, 70, 0.45)",
          ],
          "line-width": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            1.4,
            0.4,
          ],
        },
      });

      // Gminy fill — visible only at zoom ≥ 5 (the function gates anyway)
      map.addLayer({
        id: "gminy-fill",
        type: "fill",
        source: "gminy",
        "source-layer": "gminy_density",
        minzoom: 5,
        paint: {
          "fill-color": densityColorExpr(),
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.95,
            0.85,
          ],
        },
        layout: { visibility: "none" },
      });
      map.addLayer({
        id: "gminy-line",
        type: "line",
        source: "gminy",
        "source-layer": "gminy_density",
        minzoom: 5,
        paint: {
          "line-color": "rgba(60, 60, 70, 0.5)",
          "line-width": 0.3,
        },
        layout: { visibility: "none" },
      });

      // Labels above fills
      map.addLayer({
        id: "city-labels",
        type: "raster",
        source: "labels",
        paint: { "raster-opacity": 0.55 },
      });

      attachHover(map);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Listen to nav scope toggle to fly between PL/EU
  useEffect(() => {
    function onScope(e: Event) {
      const map = mapRef.current;
      if (!map) return;
      const detail = (e as CustomEvent<{ scope: "PL" | "EU" }>).detail;
      if (detail.scope === "PL") {
        map.flyTo({ center: [19.5, 52], zoom: 5, duration: 1100 });
      } else {
        map.flyTo({ center: [12.5, 51], zoom: 3.8, duration: 1100 });
      }
    }
    window.addEventListener("pa:scope", onScope as EventListener);
    return () => window.removeEventListener("pa:scope", onScope as EventListener);
  }, []);

  // Toggle visible layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const showGminy = layer === "gminy";
    ["nuts2-fill", "nuts2-line"].forEach((id) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", showGminy ? "none" : "visible");
      }
    });
    ["gminy-fill", "gminy-line"].forEach((id) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", showGminy ? "visible" : "none");
      }
    });
  }, [layer]);

  function attachHover(map: MaplibreMap): void {
    let hoveredId: string | number | null = null;
    let hoveredSource: "nuts2" | "gminy" | null = null;
    let hoveredSourceLayer: string | null = null;

    function setHoverState(
      source: "nuts2" | "gminy",
      sourceLayer: string,
      id: string | number | null,
      state: boolean,
    ): void {
      if (id == null) return;
      map.setFeatureState({ source, sourceLayer, id }, { hover: state });
    }

    function clearHover() {
      if (hoveredId != null && hoveredSource && hoveredSourceLayer) {
        setHoverState(hoveredSource, hoveredSourceLayer, hoveredId, false);
      }
      hoveredId = null;
      hoveredSource = null;
      hoveredSourceLayer = null;
      map.getCanvas().style.cursor = "";
      setHover(null);
    }

    function makeHandler(
      source: "nuts2" | "gminy",
      sourceLayer: string,
      readFeature: (f: MapGeoJSONFeature) => {
        name: string;
        code: string;
        density: number | null;
        n_lockers: number;
        population: number;
        country: string;
      },
    ) {
      return (e: maplibregl.MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0];
        if (!f) return;
        if (hoveredId !== f.id) {
          clearHover();
          hoveredId = (f.id as string | number) ?? null;
          hoveredSource = source;
          hoveredSourceLayer = sourceLayer;
          setHoverState(source, sourceLayer, hoveredId, true);
        }
        map.getCanvas().style.cursor = "pointer";
        const read = readFeature(f);
        setHover({ ...read, x: e.point.x, y: e.point.y });
      };
    }

    map.on(
      "mousemove",
      "nuts2-fill",
      makeHandler("nuts2", "nuts2_density", (f) => ({
        name: String(f.properties?.name_latn ?? f.properties?.code ?? ""),
        code: String(f.properties?.code ?? ""),
        density:
          f.properties?.lockers_per_10k != null
            ? Number(f.properties.lockers_per_10k)
            : null,
        n_lockers: Number(f.properties?.n_lockers ?? 0),
        population: Number(f.properties?.population ?? 0),
        country: String(f.properties?.country ?? ""),
      })),
    );
    map.on("mouseleave", "nuts2-fill", clearHover);

    map.on(
      "mousemove",
      "gminy-fill",
      makeHandler("gminy", "gminy_density", (f) => ({
        name: String(f.properties?.name ?? ""),
        code: String(f.properties?.teryt ?? ""),
        density:
          f.properties?.lockers_per_10k != null
            ? Number(f.properties.lockers_per_10k)
            : null,
        n_lockers: Number(f.properties?.n_lockers ?? 0),
        population: Number(f.properties?.population ?? 0),
        country: "PL",
      })),
    );
    map.on("mouseleave", "gminy-fill", clearHover);
  }

  return (
    <article
      className="panel panel-map relative flex flex-col"
      style={{ minHeight: 540 }}
    >
      <header className="panel-head">
        <div>
          <div className="panel-title">Locker density by NUTS-2 region</div>
          <div className="panel-sub">
            Lockers per 10,000 inhabitants · quantile 5-bucket · vector tiles via Martin
          </div>
        </div>
        <div role="group" aria-label="Map layer" className="flex gap-1">
          <Chip active={layer === "nuts2"} onClick={() => setLayer("nuts2")}>
            NUTS-2
          </Chip>
          <Chip
            active={layer === "gminy"}
            onClick={() => {
              setLayer("gminy");
              mapRef.current?.flyTo({ center: [19.5, 52], zoom: 6, duration: 900 });
            }}
          >
            Gminy <span className="mono">z≥5</span>
          </Chip>
        </div>
      </header>

      <div ref={containerRef} className="flex-1 min-h-0" />

      {/* Legend */}
      <div
        className="absolute z-[5]"
        style={{
          left: 16,
          bottom: 16,
          minWidth: 220,
          background: "rgba(17, 17, 19, 0.92)",
          backdropFilter: "blur(6px)",
          border: "1px solid var(--border-default)",
          padding: "12px 14px",
        }}
      >
        <div
          className="uppercase mb-2"
          style={{
            fontSize: 10.5,
            letterSpacing: "0.08em",
            color: "var(--fg-subtle)",
          }}
        >
          lockers / 10k
        </div>
        <div
          style={{
            height: 10,
            border: "1px solid var(--border-default)",
            marginBottom: 4,
            background:
              "linear-gradient(90deg, rgba(15,15,18,1) 0%, rgba(20,16,50,1) 14%, rgba(90,26,69,1) 32%, rgba(158,37,32,1) 56%, rgba(221,88,24,1) 78%, rgba(245,192,78,1) 100%)",
          }}
        />
        <div
          className="grid mono"
          style={{
            gridTemplateColumns: "repeat(5, 1fr)",
            fontSize: 10,
            color: "var(--fg-subtle)",
            marginBottom: 10,
          }}
        >
          <span>0</span><span>1</span><span>2</span><span>5</span>
          <span className="text-right">10+</span>
        </div>
        <div
          className="flex flex-col gap-1 pt-2"
          style={{ borderTop: "1px solid var(--border-subtle)" }}
        >
          <LegendExtra label="pre-launch (SE / DK / FI)" patternKind="hatch" />
          <LegendExtra label="GB excluded post-Brexit" patternKind="gb" />
        </div>
      </div>

      {/* Tooltip */}
      {hover && (
        <div
          className="absolute z-[6] pointer-events-none"
          style={{
            left: hover.x,
            top: hover.y,
            transform: "translate(-50%, -120%)",
            background: "var(--bg-surface-2)",
            border: "1px solid var(--border-default)",
            padding: "10px 12px",
            fontSize: 12,
            minWidth: 200,
            boxShadow: "0 1px 0 var(--border-default)",
          }}
        >
          <div
            style={{ fontWeight: 500, marginBottom: 6, color: "var(--fg-default)" }}
          >
            {hover.name}{" "}
            <span
              className="mono"
              style={{ color: "var(--fg-subtle)", fontWeight: 400 }}
            >
              · {hover.code}
            </span>
          </div>
          {hover.density != null ? (
            <>
              <TtRow label="Lockers / 10k" value={fmt2(hover.density)} />
              <TtRow label="Lockers" value={fmtInt(hover.n_lockers)} />
              <TtRow label="Population" value={fmtInt(hover.population)} />
            </>
          ) : (
            <TtRow label="Data" value="no records" />
          )}
        </div>
      )}

      <div
        className="absolute mono"
        style={{
          right: 16,
          bottom: 16,
          padding: "6px 10px",
          fontSize: 10,
          color: "var(--fg-subtle)",
          background: "rgba(10, 10, 11, 0.7)",
          border: "1px solid var(--border-default)",
          pointerEvents: "none",
        }}
      >
        Basemap © CartoDB · Tiles © Martin · NUTS-2 © Eurostat 2024
      </div>
    </article>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className="mono transition-colors"
      style={{
        fontSize: 11,
        padding: "4px 10px",
        background: active ? "rgba(224, 168, 46, 0.06)" : "var(--bg-surface-2)",
        border: `1px solid ${active ? "var(--accent-lo)" : "var(--border-default)"}`,
        color: active ? "var(--accent)" : "var(--fg-muted)",
      }}
    >
      {children}
    </button>
  );
}

function LegendExtra({
  label,
  patternKind,
}: {
  label: string;
  patternKind: "hatch" | "gb";
}) {
  const swatchStyle: React.CSSProperties =
    patternKind === "hatch"
      ? {
          background:
            "repeating-linear-gradient(45deg, #9E2520 0 1.5px, transparent 1.5px 4px), var(--bg-surface-2)",
        }
      : {
          background: "var(--bg-surface-2)",
          border: "1px dashed var(--border-strong)",
        };
  return (
    <div
      className="flex items-center"
      style={{ fontSize: 11, color: "var(--fg-muted)" }}
    >
      <i
        className="inline-block mr-1.5 align-[-1px]"
        style={{ width: 9, height: 9, ...swatchStyle }}
      />
      {label}
    </div>
  );
}

function TtRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex justify-between gap-4"
      style={{ color: "var(--fg-muted)", fontSize: 11.5 }}
    >
      <span>{label}</span>
      <span className="mono" style={{ color: "var(--fg-default)" }}>
        {value}
      </span>
    </div>
  );
}

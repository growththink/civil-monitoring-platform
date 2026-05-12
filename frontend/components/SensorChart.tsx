"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import type { Sensor, TimeSeriesPoint } from "@/lib/types";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface Props {
  sensor: Sensor;
  points: TimeSeriesPoint[];
  height?: number;
}

export function SensorChart({ sensor, points, height = 320 }: Props) {
  const option = useMemo(() => {
    const data = points.map((p) => [p.ts, p.value]);

    const markLines: any[] = [];
    for (const t of sensor.thresholds) {
      const color = t.level === "critical" ? "#ef4444" : "#f59e0b";
      if (t.max_value !== null && t.max_value !== undefined) {
        markLines.push({
          yAxis: t.max_value,
          lineStyle: { color, type: "dashed" },
          label: { formatter: `${t.level} max ${t.max_value}`, color },
        });
      }
      if (t.min_value !== null && t.min_value !== undefined) {
        markLines.push({
          yAxis: t.min_value,
          lineStyle: { color, type: "dashed" },
          label: { formatter: `${t.level} min ${t.min_value}`, color },
        });
      }
    }
    if (sensor.initial_baseline !== null && sensor.initial_baseline !== undefined) {
      markLines.push({
        yAxis: sensor.initial_baseline,
        lineStyle: { color: "#0ea5e9", type: "solid", opacity: 0.5 },
        label: { formatter: "baseline", color: "#0ea5e9" },
      });
    }

    return {
      backgroundColor: "transparent",
      grid: { left: 50, right: 20, top: 30, bottom: 40 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1f2533",
        borderColor: "#3f4757",
        textStyle: { color: "#e7e9ed" },
        formatter: (params: any) => {
          const p = params[0];
          return `<div>${p.axisValueLabel}</div><div><b>${p.value[1].toFixed(4)} ${sensor.unit}</b></div>`;
        },
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: "#3f4757" } },
        axisLabel: { color: "#a1a8b6" },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        name: sensor.unit,
        nameTextStyle: { color: "#a1a8b6" },
        axisLine: { lineStyle: { color: "#3f4757" } },
        axisLabel: { color: "#a1a8b6" },
        splitLine: { lineStyle: { color: "#1f2533" } },
      },
      dataZoom: [
        { type: "inside", throttle: 50 },
        { type: "slider", height: 18, bottom: 5, borderColor: "#3f4757",
          textStyle: { color: "#a1a8b6" } },
      ],
      series: [
        {
          name: sensor.name,
          type: "line",
          smooth: false,
          showSymbol: false,
          sampling: "lttb",
          lineStyle: { color: "#0ea5e9", width: 1.5 },
          areaStyle: {
            color: {
              type: "linear", x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(14,165,233,0.25)" },
                { offset: 1, color: "rgba(14,165,233,0.0)" },
              ],
            },
          },
          markLine: {
            symbol: ["none", "none"],
            silent: true,
            data: markLines,
          },
          data,
        },
      ],
    };
  }, [points, sensor]);

  return (
    <div style={{ height }}>
      <ReactECharts
        option={option}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
        notMerge
      />
    </div>
  );
}

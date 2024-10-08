"use client"

import * as React from "react"
import { CartesianGrid, Line, LineChart, XAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

export const description = "An interactive line chart"

async function fetchFinancialData(symbol: string) {
    const response = await fetch(`https://host.zzimm.com/api/income/q/${symbol}`)
    const data = await response.json()
    return data
  }

const chartConfig = {
  views: {
    label: "$",
  },
  EBITDA: {
    label: "EBITDA",
    color: "hsl(var(--chart-1))",
  },
  TotalRevenue: {
    label: "Total Revenue",
    color: "hsl(var(--chart-2))",
  },
  BasicEPS: {
    label: "Earnigns Per Share",
    color: "hsl(var(--chart-3))",
  },
} satisfies ChartConfig

interface IncomeChartDisplayProps {
  initialSymbol: string
}

export function IncomeChartDisplay({initialSymbol }: IncomeChartDisplayProps) {
  const [chartData, setChartData] = React.useState([])
  const [loading, setLoading] = React.useState(true)
  const [activeChart, setActiveChart] =
    React.useState<keyof typeof chartConfig>("EBITDA")

  React.useEffect(() => {
    fetchFinancialData(initialSymbol).then((data) => {
      // Process the data to extract the necessary information for charting
      // drop rows where periodType == TTM
        // if we do not do this, the chart will be erratic and appear to be missing data
      data = data.filter((item: any) => item.periodType.toLowerCase() !== "ttm")

      const formattedData = data.map((item: any) => ({
        date: item.asOfDate,
        EBITDA: parseFloat(item.EBITDA),
        TotalRevenue: parseFloat(item.TotalRevenue),
        BasicEPS: parseFloat(item.BasicEPS),
      }))
      setChartData(formattedData)
      setLoading(false)
    })
  }, [initialSymbol])

  return (
    <Card>
      <CardHeader className="flex flex-col items-stretch space-y-0 border-b p-0 sm:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-1 px-2 py-2 sm:py-2">
          <CardDescription>
            Historical income data for {initialSymbol} 
          </CardDescription>
        </div>
        <div className="flex">
          {["EBITDA", "TotalRevenue", "BasicEPS"].map((key) => {
            const chart = key as keyof typeof chartConfig
            return (
                <button
                    key={chart}
                    data-active={activeChart === chart}
                    className="flex flex-1 flex-col justify-center gap-1 border-t px-2 py-1 text-left even:border-l data-[active=true]:bg-muted/50 sm:border-l sm:border-t-0 sm:px-2 sm:py-1"
                    onClick={() => setActiveChart(chart)}
                >
                <span className="text-xs text-muted-foreground">
                  {chartConfig[chart].label}
                </span>
              </button>
            )
          })}
        </div>
      </CardHeader>
      <CardContent className="px-2 sm:p-6">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[250px] w-full"
        >
          <LineChart
            accessibilityLayer
            data={chartData}
            margin={{
              left: 12,
              right: 12,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value)
                return date.toLocaleDateString("en-US", {
                  month: "short",
                  year: "numeric",
                })
              }}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-[150px]"
                  nameKey="views"
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })
                  }}
                />
              }
            />
            <Line
              dataKey={activeChart}
              type="monotone"
              stroke={`var(--color-${activeChart})`}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartContainer>
        <span className="font-semibold">{initialSymbol} - {chartConfig[activeChart].label}</span>
      </CardContent>
    </Card>
  )
}
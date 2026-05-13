/**
 * Verifies the generated hey-api SDK end-to-end against the local backend.
 * Run via: pnpm tsx scripts/codegen-smoke.ts
 */
import { client } from '../lib/api/client.gen'
import {
  getNetworkSummaryApiV1KpiSummaryGet,
  topNuts2ApiV1DensityNuts2TopGet,
} from '../lib/api/sdk.gen'

client.setConfig({ baseUrl: 'http://localhost:8080' })

async function main(): Promise<void> {
  const kpi = await getNetworkSummaryApiV1KpiSummaryGet()
  console.log('Network summary:', kpi.data?.data)

  const top = await topNuts2ApiV1DensityNuts2TopGet({ query: { limit: 5 } })
  console.log('Top 5 NUTS-2:')
  for (const row of top.data?.data ?? []) {
    console.log(`  ${row.country} ${row.name_latn}: ${row.lockers_per_10k}`)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})

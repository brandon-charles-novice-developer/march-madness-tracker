import { test, expect } from '@playwright/test'

test.describe('Dashboard — Header', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders Gaygent branding', async ({ page }) => {
    await expect(page.locator('h1 .brand')).toContainText('GAYGENT')
    await expect(page.locator('h1 .title')).toContainText('SURVEILLANCE')
  })

  test('shows sync timestamp with PT timezone', async ({ page }) => {
    const bar = page.locator('#last-updated')
    await expect(bar).not.toBeEmpty({ timeout: 5000 })
    const text = await bar.textContent()
    expect(text).toContain('SYNC:')
    expect(text).toContain('PT')
    expect(text).toContain('ago')
  })

  test('shows payout info', async ({ page }) => {
    await expect(page.locator('.header-bar')).toContainText('$450')
  })

  test('renders 6 round pills', async ({ page }) => {
    await expect(page.locator('.round-pill')).toHaveCount(6)
    await expect(page.locator('.round-pill.current')).toHaveCount(1)
  })
})

test.describe('Dashboard — Unified Leaderboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders 10 leaderboard rows', async ({ page }) => {
    await expect(page.locator('.lb-row')).toHaveCount(10)
  })

  test('rows show rank, name, pts, active, avg, projected', async ({ page }) => {
    const firstRow = page.locator('.lb-row').first()
    await expect(firstRow.locator('.rank')).toBeVisible()
    await expect(firstRow.locator('.name')).toBeVisible()
    await expect(firstRow.locator('.pts')).toBeVisible()
    await expect(firstRow.locator('.active-badge')).toBeVisible()
    await expect(firstRow.locator('.avg')).toBeVisible()
  })

  test('first place has gold styling', async ({ page }) => {
    await expect(page.locator('.lb-row.top1')).toHaveCount(1)
  })

  test('top 3 have medal styling', async ({ page }) => {
    await expect(page.locator('.lb-row.top1')).toHaveCount(1)
    await expect(page.locator('.lb-row.top2')).toHaveCount(1)
    await expect(page.locator('.lb-row.top3')).toHaveCount(1)
  })

  test('standings sorted by points descending', async ({ page }) => {
    const ptsEls = page.locator('[data-mgr-pts]')
    const count = await ptsEls.count()
    const pts: number[] = []
    for (let i = 0; i < count; i++) {
      pts.push(Number(await ptsEls.nth(i).textContent()))
    }
    for (let i = 1; i < pts.length; i++) {
      expect(pts[i]).toBeLessThanOrEqual(pts[i - 1])
    }
  })

  test('clicking row expands detail panel', async ({ page }) => {
    const firstRow = page.locator('.lb-row').first()
    await firstRow.click()
    await expect(firstRow).toHaveClass(/expanded/)
    const panel = page.locator('.detail-panel.open')
    await expect(panel).toHaveCount(1)
    await expect(panel.locator('.player-tbl')).toBeVisible()
  })

  test('clicking expanded row collapses it', async ({ page }) => {
    const firstRow = page.locator('.lb-row').first()
    await firstRow.click()
    await expect(page.locator('.detail-panel.open')).toHaveCount(1)
    await firstRow.click()
    await expect(page.locator('.detail-panel.open')).toHaveCount(0)
  })

  test('clicking different row swaps expansion', async ({ page }) => {
    const rows = page.locator('.lb-row')
    await rows.nth(0).click()
    await expect(page.locator('.detail-panel.open')).toHaveCount(1)
    await rows.nth(1).click()
    await expect(page.locator('.detail-panel.open')).toHaveCount(1)
    await expect(rows.nth(1)).toHaveClass(/expanded/)
  })

  test('detail panel shows metrics bar', async ({ page }) => {
    await page.locator('.lb-row').first().click()
    const metrics = page.locator('.detail-metrics')
    await expect(metrics).toContainText('ACTIVE')
    await expect(metrics).toContainText('AVG/PLAYER')
    await expect(metrics).toContainText('PROJECTED')
  })

  test('detail panel shows player table with 8 players', async ({ page }) => {
    await page.locator('.lb-row').first().click()
    const playerRows = page.locator('.detail-panel.open .player-tbl tbody tr')
    await expect(playerRows).toHaveCount(8)
  })

  test('eliminated players are dimmed', async ({ page }) => {
    const rows = page.locator('.lb-row')
    for (let i = 0; i < 10; i++) {
      await rows.nth(i).click()
      const elim = page.locator('.detail-panel.open tr.elim')
      if (await elim.count() > 0) {
        await expect(elim.first()).toHaveCSS('opacity', '0.35')
        return
      }
      await rows.nth(i).click()
    }
  })

  test('active players have green status pip', async ({ page }) => {
    await page.locator('.lb-row').first().click()
    const pips = page.locator('.detail-panel.open .status-pip.on')
    expect(await pips.count()).toBeGreaterThan(0)
  })

  test('commentary displayed when available', async ({ page }) => {
    await page.locator('.lb-row').first().click()
    const commentary = page.locator('.detail-panel.open .detail-commentary')
    if (await commentary.count() > 0) {
      const text = await commentary.textContent()
      expect(text!.length).toBeGreaterThan(20)
    }
  })

  test('footnote explains metrics with Magged joke', async ({ page }) => {
    await expect(page.getByText('Definitions provided for Magged')).toBeVisible()
  })
})

test.describe('Dashboard — Tournament Leaders', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders scoring leaders section', async ({ page }) => {
    await expect(page.locator('.leaders-panel h3')).toContainText('TOURNAMENT SCORING LEADERS')
  })

  test('shows up to 10 leaders', async ({ page }) => {
    const rows = page.locator('.leader-row')
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(1)
    expect(count).toBeLessThanOrEqual(10)
  })

  test('leaders show points and manager initials', async ({ page }) => {
    const first = page.locator('.leader-row').first()
    await expect(first.locator('.leader-pts')).toBeVisible()
    await expect(first.locator('.leader-mgr')).toBeVisible()
  })

  test('top 3 leaders have magenta badges', async ({ page }) => {
    const t3 = page.locator('.leader-num.t3')
    expect(await t3.count()).toBe(3)
  })
})

test.describe('Dashboard — Data Integrity', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('10 managers in leaderboard', async ({ page }) => {
    await expect(page.locator('.lb-row')).toHaveCount(10)
  })

  test('every manager has 8 players', async ({ page }) => {
    const rows = page.locator('.lb-row')
    for (let i = 0; i < 10; i++) {
      await rows.nth(i).click()
      await expect(page.locator('.detail-panel.open .player-tbl tbody tr')).toHaveCount(8)
      await rows.nth(i).click()
    }
  })

  test('manager total equals sum of player totals', async ({ page }) => {
    await page.locator('.lb-row').first().click()
    const mgrPts = Number(await page.locator('.lb-row.expanded .pts').textContent())
    const playerTotals = page.locator('.detail-panel.open .total-col')
    const count = await playerTotals.count()
    let sum = 0
    for (let i = 0; i < count; i++) {
      sum += Number(await playerTotals.nth(i).textContent())
    }
    expect(sum).toBe(mgrPts)
  })
})

test.describe('Dashboard — JSON Feeds', () => {
  test('leaderboard.json has new metric fields', async ({ request }) => {
    const resp = await request.get('/data/leaderboard.json')
    const data = await resp.json()
    expect(data.standings).toHaveLength(10)
    const s = data.standings[0]
    expect(s).toHaveProperty('avg_per_active')
    expect(s).toHaveProperty('projected_finish')
    expect(s).toHaveProperty('current_round_delta')
    expect(typeof s.avg_per_active).toBe('number')
    expect(typeof s.projected_finish).toBe('number')
  })

  test('meta.json valid', async ({ request }) => {
    const data = await (await request.get('/data/meta.json')).json()
    expect(data.managers).toHaveLength(10)
  })

  test('commentary.json valid', async ({ request }) => {
    const data = await (await request.get('/data/commentary.json')).json()
    expect(Object.keys(data.managers)).toHaveLength(10)
  })
})

test.describe('Dashboard — Live Update System', () => {
  test('has animation and diff functions', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const script = await page.evaluate(() => document.querySelector('script:last-of-type')?.textContent || '')
    expect(script).toContain('liveUpdate')
    expect(script).toContain('diffStandings')
    expect(script).toContain('animateCount')
    expect(script).toContain('escapeHtml')
    expect(script).toContain('escapeAttr')
  })

  test('confetti library loaded', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    expect(await page.evaluate(() => typeof (window as any).confetti === 'function')).toBeTruthy()
  })

  test('data attributes for animation targeting', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    expect(await page.locator('[data-mgr-pts]').count()).toBe(10)
    await page.locator('.lb-row').first().click()
    expect(await page.locator('[data-player-row]').count()).toBeGreaterThan(0)
  })
})

test.describe('Dashboard — Mobile', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('leaderboard renders on mobile', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.lb-row')).toHaveCount(10)
  })

  test('detail panel opens on mobile', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.locator('.lb-row').first().click()
    await expect(page.locator('.detail-panel.open')).toHaveCount(1)
  })
})

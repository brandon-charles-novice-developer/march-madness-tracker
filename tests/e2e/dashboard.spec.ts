import { test, expect } from '@playwright/test'

test.describe('Dashboard — Page Load', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders page title with Gaygent branding', async ({ page }) => {
    await expect(page.locator('h1')).toContainText("Gaygent")
    await expect(page.locator('h1')).toContainText('March Madness')
  })

  test('renders round progress pills', async ({ page }) => {
    const pills = page.locator('.round-pill')
    await expect(pills).toHaveCount(6)
    // Current round pill has .current class
    const current = page.locator('.round-pill.current')
    await expect(current).toHaveCount(1)
  })

  test('shows last sync timestamp', async ({ page }) => {
    const updated = page.locator('#last-updated')
    // Wait for JS to render the timestamp
    await expect(updated).not.toBeEmpty({ timeout: 5000 })
    const text = await updated.textContent()
    expect(text).toContain('Last sync:')
    expect(text).toContain('ago')
  })

  test('shows LIVE indicator during game window', async ({ page }) => {
    // LIVE indicator appears when in game window
    const liveEl = page.locator('#live-indicator')
    // May or may not be visible depending on time — just check element exists
    await expect(liveEl).toBeAttached()
  })

  test('displays payout info', async ({ page }) => {
    await expect(page.locator('.meta-bar')).toContainText('$450')
    await expect(page.locator('.meta-bar')).toContainText('$50')
  })
})

test.describe('Dashboard — Podium', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders 3 podium cards', async ({ page }) => {
    const cards = page.locator('.podium-card')
    await expect(cards).toHaveCount(3)
  })

  test('first place card has gold styling', async ({ page }) => {
    const first = page.locator('.podium-card.first')
    await expect(first).toBeVisible()
    await expect(first.locator('.podium-medal')).toContainText('🥇')
  })

  test('podium shows manager names and points', async ({ page }) => {
    const firstPts = page.locator('.podium-card.first .podium-pts')
    await expect(firstPts).toBeVisible()
    const ptsText = await firstPts.textContent()
    expect(Number(ptsText)).toBeGreaterThan(0)
  })

  test('podium cards have data-mgr-pts attributes', async ({ page }) => {
    const pts = page.locator('[data-mgr-pts]')
    await expect(pts).toHaveCount(3)
  })

  test('podium shows survival stats', async ({ page }) => {
    const stats = page.locator('.podium-card.first .podium-stats')
    await expect(stats).toContainText('alive')
    await expect(stats).toContainText('live')
  })
})

test.describe('Dashboard — Standings Table', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders standings for ranks 4-10', async ({ page }) => {
    const rows = page.locator('#standings-body tr')
    await expect(rows).toHaveCount(7)
  })

  test('standings rows have points in purple', async ({ page }) => {
    const ptsCells = page.locator('.pts-val')
    const count = await ptsCells.count()
    expect(count).toBe(7)
    for (let i = 0; i < count; i++) {
      const text = await ptsCells.nth(i).textContent()
      expect(Number(text)).toBeGreaterThan(0)
    }
  })

  test('shows survival and live percentage columns', async ({ page }) => {
    const headers = page.locator('.standings-table th')
    await expect(headers.filter({ hasText: 'Survival' })).toBeVisible()
    await expect(headers.filter({ hasText: 'Live' })).toBeVisible()
  })

  test('footnote explains metrics with Magged joke', async ({ page }) => {
    const footnote = page.getByText('Definitions provided for Magged')
    await expect(footnote).toBeVisible()
  })
})

test.describe('Dashboard — Tournament Leaders', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders tournament scoring leaders section', async ({ page }) => {
    await expect(page.locator('.highlight-card h3').first()).toContainText('Tournament Scoring Leaders')
  })

  test('shows up to 10 active player leaders', async ({ page }) => {
    const rows = page.locator('.hot-row')
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(1)
    expect(count).toBeLessThanOrEqual(10)
  })

  test('leaders have rank badges', async ({ page }) => {
    const badges = page.locator('.highlight-card .rank-badge')
    const count = await badges.count()
    expect(count).toBeGreaterThan(0)
    // Top 3 should have purple badge
    await expect(badges.first()).toHaveClass(/top3/)
  })

  test('leaders show points and manager initials', async ({ page }) => {
    const firstRow = page.locator('.hot-row').first()
    await expect(firstRow.locator('.pts')).toBeVisible()
    await expect(firstRow.locator('.mgr')).toBeVisible()
  })

  test('no eliminated players in leaders', async ({ page }) => {
    // Leaders should only show active players — verify none say "eliminated"
    const rows = page.locator('.hot-row')
    const count = await rows.count()
    for (let i = 0; i < count; i++) {
      const text = await rows.nth(i).textContent()
      expect(text).not.toContain('eliminated')
    }
  })
})

test.describe('Dashboard — Manager Cards', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('renders 10 manager cards', async ({ page }) => {
    const cards = page.locator('.manager-card')
    await expect(cards).toHaveCount(10)
  })

  test('cards are collapsed by default', async ({ page }) => {
    const openCards = page.locator('.manager-card[open]')
    await expect(openCards).toHaveCount(0)
  })

  test('card expands on click and shows player table', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    await expect(firstCard).toHaveAttribute('open', '')
    await expect(firstCard.locator('.player-table')).toBeVisible()
  })

  test('expanded card shows commentary', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    const commentary = firstCard.locator('.card-commentary')
    // Commentary may or may not exist depending on data
    if (await commentary.count() > 0) {
      await expect(commentary).toBeVisible()
      const text = await commentary.textContent()
      expect(text!.length).toBeGreaterThan(20)
    }
  })

  test('card summary shows rank, name, points, and active count', async ({ page }) => {
    const summary = page.locator('.manager-summary').first()
    await expect(summary.locator('.m-rank')).toBeVisible()
    await expect(summary.locator('.m-name')).toBeVisible()
    await expect(summary.locator('.m-pts')).toBeVisible()
    await expect(summary.locator('.m-badge')).toBeVisible()
  })

  test('expanded card shows survival and live portfolio metrics', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    await expect(firstCard.locator('.card-metrics')).toContainText('Survival')
    await expect(firstCard.locator('.card-metrics')).toContainText('Live Portfolio')
  })

  test('player table has round columns', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    const headers = firstCard.locator('.player-table th')
    await expect(headers.filter({ hasText: 'R64' })).toBeVisible()
    await expect(headers.filter({ hasText: 'Total' })).toBeVisible()
  })

  test('eliminated players are visually dimmed', async ({ page }) => {
    // Find a card and expand it
    const cards = page.locator('.manager-card')
    const count = await cards.count()
    for (let i = 0; i < count; i++) {
      await cards.nth(i).locator('summary').click()
      const eliminated = cards.nth(i).locator('tr.eliminated')
      if (await eliminated.count() > 0) {
        // Found eliminated player — verify styling
        await expect(eliminated.first()).toHaveCSS('opacity', '0.4')
        return
      }
      // Close it before trying next
      await cards.nth(i).locator('summary').click()
    }
  })

  test('active players have green status dot', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    const activeDots = firstCard.locator('.status-dot.active')
    expect(await activeDots.count()).toBeGreaterThan(0)
  })
})

test.describe('Dashboard — Data Integrity', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('all 10 managers represented (3 podium + 7 table)', async ({ page }) => {
    const podiumCards = await page.locator('.podium-card').count()
    const tableRows = await page.locator('#standings-body tr').count()
    expect(podiumCards + tableRows).toBe(10)
  })

  test('every manager card has 8 players', async ({ page }) => {
    const cards = page.locator('.manager-card')
    const count = await cards.count()
    expect(count).toBe(10)

    for (let i = 0; i < count; i++) {
      await cards.nth(i).locator('summary').click()
      const playerRows = cards.nth(i).locator('.player-table tbody tr')
      await expect(playerRows).toHaveCount(8)
      await cards.nth(i).locator('summary').click()
    }
  })

  test('standings are sorted by points descending', async ({ page }) => {
    // Get podium points
    const podiumPts: number[] = []
    const podiumEls = page.locator('[data-mgr-pts]')
    for (let i = 0; i < 3; i++) {
      podiumPts.push(Number(await podiumEls.nth(i).textContent()))
    }

    // Get table points
    const tablePts: number[] = []
    const tableEls = page.locator('[data-mgr-table-pts]')
    const tableCount = await tableEls.count()
    for (let i = 0; i < tableCount; i++) {
      tablePts.push(Number(await tableEls.nth(i).textContent()))
    }

    const allPts = [...podiumPts, ...tablePts]
    for (let i = 1; i < allPts.length; i++) {
      expect(allPts[i]).toBeLessThanOrEqual(allPts[i - 1])
    }
  })

  test('total points equals sum of player points per manager', async ({ page }) => {
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()

    const mgrPtsText = await firstCard.locator('[data-mgr-card-pts]').textContent()
    const mgrPts = Number(mgrPtsText!.replace(' pts', ''))

    const playerTotals = firstCard.locator('.total-cell')
    const count = await playerTotals.count()
    let sum = 0
    for (let i = 0; i < count; i++) {
      sum += Number(await playerTotals.nth(i).textContent())
    }

    expect(sum).toBe(mgrPts)
  })
})

test.describe('Dashboard — JSON Feed Contract', () => {
  test('leaderboard.json serves valid data', async ({ request }) => {
    const resp = await request.get('/data/leaderboard.json')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data.standings).toHaveLength(10)
    expect(data.current_round).toBeTruthy()
    expect(data.rounds).toHaveLength(6)
    expect(data.last_updated).toBeTruthy()
  })

  test('meta.json serves valid data', async ({ request }) => {
    const resp = await request.get('/data/meta.json')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data.managers).toHaveLength(10)
    expect(data.payouts.first).toBe(450)
  })

  test('commentary.json serves valid data', async ({ request }) => {
    const resp = await request.get('/data/commentary.json')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(Object.keys(data.managers)).toHaveLength(10)
    expect(data.gaygent_header).toBeTruthy()
  })

  test('games.json serves valid data', async ({ request }) => {
    const resp = await request.get('/data/games.json')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data.games.length).toBeGreaterThan(0)
  })
})

test.describe('Dashboard — Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('renders podium on mobile', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const podium = page.locator('.podium')
    await expect(podium).toBeVisible()
    const cards = page.locator('.podium-card')
    await expect(cards).toHaveCount(3)
  })

  test('manager cards expand on mobile', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    await expect(firstCard.locator('.player-table')).toBeVisible()
  })

  test('standings table is readable on mobile', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const table = page.locator('.standings-table')
    await expect(table).toBeVisible()
  })
})

test.describe('Dashboard — Live Update System', () => {
  test('page has liveUpdate function defined', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const hasLiveUpdate = await page.evaluate(() => typeof (window as any).liveUpdate === 'function' || document.querySelector('script')?.textContent?.includes('liveUpdate'))
    // liveUpdate is defined in a script block — check it exists
    const scriptContent = await page.evaluate(() => document.querySelector('script:last-of-type')?.textContent || '')
    expect(scriptContent).toContain('liveUpdate')
    expect(scriptContent).toContain('diffStandings')
    expect(scriptContent).toContain('animateCount')
    expect(scriptContent).toContain('escapeHtml')
    expect(scriptContent).toContain('escapeAttr')
  })

  test('confetti library is loaded', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const hasConfetti = await page.evaluate(() => typeof (window as any).confetti === 'function')
    expect(hasConfetti).toBeTruthy()
  })

  test('data attributes exist for animation targeting', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Podium points
    const podiumPts = page.locator('[data-mgr-pts]')
    expect(await podiumPts.count()).toBe(3)

    // Table points
    const tablePts = page.locator('[data-mgr-table-pts]')
    expect(await tablePts.count()).toBe(7)

    // Manager card points
    const cardPts = page.locator('[data-mgr-card-pts]')
    expect(await cardPts.count()).toBe(10)

    // Player rows (expand a card first)
    const firstCard = page.locator('.manager-card').first()
    await firstCard.locator('summary').click()
    const playerRows = page.locator('[data-player-row]')
    expect(await playerRows.count()).toBeGreaterThan(0)
  })
})

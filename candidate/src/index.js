'use strict';
require('dotenv').config();

const { readSheet } = require('./services/sheets.service');
const DRY_RUN = process.env.DRY_RUN === 'true';

/**
 * Convert raw sheet rows → array of objects
 */
function rowsToObjects(rows) {
  if (!rows || rows.length === 0) return [];

  const [header, ...data] = rows;

  return data.map((row, rowIndex) => {
    const obj = { __rowNum: rowIndex + 2 }; // +2 vì sheet bắt đầu từ row 2 (row 1 là header)

    header.forEach((col, i) => {
      obj[col.trim()] = row[i] ?? null;
    });

    return obj;
  });
}

/**
 * Print Data Quality Report
 */
function printReport(report) {
  console.log('\n================================================');
  console.log('  DATA QUALITY REPORT');
  console.log('================================================\n');

  console.log(`── AUTO-CORRECTIONS (${report.autoCorrections.length}) ──`);
  report.autoCorrections.forEach((r) => {
    console.log(`  [${r.sheet}] row ${r.row}: ${r.message}`);
  });

  console.log(`\n── WARNINGS (${report.warnings.length}) ──`);
  report.warnings.forEach((r) => {
    console.log(`  [${r.sheet}] row ${r.row}: ${r.message}`);
  });

  console.log(`\n── REJECTIONS (${report.rejections.length}) ──`);
  report.rejections.forEach((r) => {
    console.log(`  [${r.sheet}] row ${r.row}: ${r.message}`);
  });

  console.log('\n── SUMMARY ──');
  console.log(`  Auto-corrections : ${report.autoCorrections.length}`);
  console.log(`  Warnings         : ${report.warnings.length}`);
  console.log(`  Rejections       : ${report.rejections.length}`);
  console.log('================================================\n');
}

async function main() {
  if (DRY_RUN) {
    console.log('⚠  DRY RUN — no database writes will occur.\n');
  }

  // ============================================================
  // Step 1 — Read all sheets in parallel
  // ============================================================

  console.log('Reading Google Sheets…');

  const [empRows, projRows, allocRows] = await Promise.all([
    readSheet(process.env.EMPLOYEES_SHEET_ID, process.env.EMPLOYEES_RANGE),
    readSheet(process.env.PROJECTS_SHEET_ID, process.env.PROJECTS_RANGE),
    readSheet(process.env.ALLOCATIONS_SHEET_ID, process.env.ALLOCATIONS_RANGE),
  ]);

  console.log(
    `  employees: ${empRows.length} rows  |  projects: ${projRows.length} rows  |  allocations: ${allocRows.length} rows`
  );

  const rawEmployees = rowsToObjects(empRows);
  const rawProjects = rowsToObjects(projRows);
  const rawAllocations = rowsToObjects(allocRows);

  // ============================================================
  // Prepare report object
  // ============================================================

  const report = {
    autoCorrections: [],
    warnings: [],
    rejections: [],
  };

  // ============================================================
  // Step 2 — Employees
  // ============================================================

  console.log('\nTransforming employees…');

  // TODO: implement transformEmployees
  const employees = rawEmployees; // placeholder

  console.log(`  ${employees.length} / ${rawEmployees.length} rows accepted`);

  // TODO: upsertEmployees(employees, DRY_RUN)

  // ============================================================
  // Step 3 — Projects
  // ============================================================

  console.log('\nTransforming projects…');

  const projects = rawProjects; // placeholder

  console.log(`  ${projects.length} / ${rawProjects.length} rows accepted`);

  // TODO: upsertProjects(projects, DRY_RUN)

  // ============================================================
  // Step 4 — Allocations
  // ============================================================

  console.log('\nTransforming allocations…');

  const allocations = rawAllocations; // placeholder

  console.log(`  ${allocations.length} / ${rawAllocations.length} rows accepted`);

  // TODO:
  // - validate referential integrity
  // - upsertAllocations(allocations, DRY_RUN)

  // ============================================================
  // Step 5 — Over-allocation detection
  // ============================================================

  // TODO: detectOverAllocations(allocations, report)

  // ============================================================
  // Step 6 — Log sync to DB
  // ============================================================

  // TODO: insert into sync_log

  // ============================================================
  // Step 7 — Print Report
  // ============================================================

  printReport(report);
}

main().catch((err) => {
  console.error('\nFatal pipeline error:', err.message);
  if (process.env.DEBUG) console.error(err.stack);
  process.exit(1);
});

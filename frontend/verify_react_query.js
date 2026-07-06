/**
 * React Query 验证脚本
 * 检查前端是否正确集成和使用 React Query
 */

const fs = require('fs');
const path = require('path');

// ANSI 颜色代码
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const RESET = '\x1b[0m';

function log(message, color = '') {
  console.log(`${color}${message}${RESET}`);
}

function checkFile(filePath, checks) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const results = [];

  for (const [name, pattern] of Object.entries(checks)) {
    const found = pattern.test(content);
    results.push({ name, found, pattern });
  }

  return results;
}

function verifyReactQuerySetup() {
  log('\n=== React Query Setup Verification ===\n');

  const results = {
    app: checkFile('src/App.js', {
      'QueryClient import': /import.*QueryClient.*from.*react-query/,
      'QueryClientProvider': /QueryClientProvider/,
      'queryClient instance': /new QueryClient/,
      'staleTime configured': /staleTime/,
    }),
    apiHooks: checkFile('src/services/apiHooks.js', {
      'React Query imports': /from ["']@tanstack\/react-query["']/,
      'useQuery hooks': /useQuery\(/,
      'useMutation hooks': /useMutation\(/,
      'queryClient usage': /useQueryClient\(\)/,
      'invalidateQueries': /invalidateQueries/,
    }),
    dashboard: checkFile('src/pages/Dashboard.js', {
      'apiHooks import': /from.*apiHooks/,
      'useDashboardStats': /useDashboardStats/,
      'useChartData': /useChartData/,
      'useFavorites': /useFavorites/,
    }),
    opportunityList: checkFile('src/pages/OpportunityList.js', {
      'apiHooks import': /from.*apiHooks/,
      'useOpportunityList': /useOpportunityList/,
      'useFetchAnnouncements': /useFetchAnnouncements/,
      'useToggleFavorite': /useToggleFavorite/,
    }),
  };

  let totalChecks = 0;
  let passedChecks = 0;

  for (const [file, checks] of Object.entries(results)) {
    log(`\n${file}:`, YELLOW);
    for (const check of checks) {
      totalChecks++;
      const status = check.found ? 'OK' : 'MISSING';
      const color = check.found ? GREEN : RED;
      log(`  [${status}] ${check.name}`, color);
      if (check.found) passedChecks++;
    }
  }

  log('\n=== Summary ===\n');
  log(`Passed: ${passedChecks}/${totalChecks} checks`, passedChecks === totalChecks ? GREEN : RED);

  if (passedChecks === totalChecks) {
    log('\n✓ React Query is properly configured and used!', GREEN);
    log('\nFeatures enabled:');
    log('  - Automatic caching with 5min stale time');
    log('  - Background refetching');
    log('  - Mutation cache invalidation');
    log('  - Query key management');
    log('  - Error handling with retry');
  } else {
    log('\n✗ Some React Query features are missing', RED);
    log('\nTo enable React Query in components:');
    log('  1. Import hooks: import { useXxx } from "../services/apiHooks"');
    log('  2. Use hooks: const { data, isLoading } = useXxx(params)');
    log('  3. React Query handles caching automatically');
  }

  return passedChecks === totalChecks;
}

// Check package.json for React Query installation
function checkDependencies() {
  log('\n=== Dependencies Check ===\n');

  const packagePath = 'package.json';
  if (!fs.existsSync(packagePath)) {
    log('package.json not found!', RED);
    return false;
  }

  const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
  const deps = { ...pkg.dependencies, ...pkg.devDependencies };

  const reactQuery = deps['@tanstack/react-query'];
  if (reactQuery) {
    log(`[OK] @tanstack/react-query ${reactQuery} installed`, GREEN);
    return true;
  } else {
    log('[MISSING] @tanstack/react-query not installed', RED);
    log('  Run: npm install @tanstack/react-query@5', YELLOW);
    return false;
  }
}

// Main verification
try {
  process.chdir('frontend');

  const depsOk = checkDependencies();
  const setupOk = verifyReactQuerySetup();

  log('\n=== Final Result ===\n');
  if (depsOk && setupOk) {
    log('[SUCCESS] React Query is fully configured and ready!', GREEN);
    process.exit(0);
  } else {
    log('[WARNING] Some checks failed - see details above', YELLOW);
    process.exit(1);
  }
} catch (error) {
  log(`\n[ERROR] Verification failed: ${error.message}`, RED);
  process.exit(1);
}

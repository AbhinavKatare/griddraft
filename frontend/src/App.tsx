import { Suspense, lazy, useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, motion } from 'motion/react';
import { Header } from './components/Header.tsx';
import { ControlBar } from './components/ControlBar.tsx';
import { HeroChartSkeleton } from './components/ui/LoadingSkeleton.tsx';
import { ToastContainer } from './components/ui/ToastContainer.tsx';
import { useUrlState } from './hooks/useUrlState.ts';
import { useKeepAlive } from './hooks/useKeepAlive.ts';
import { viewTransitionVariants } from './design/motion.ts';
import type { ToastMessage, ViewTab } from './types.ts';

// Lazy-loaded route and view bundles for optimal code-splitting and rapid initial paint
const DecisionView = lazy(() =>
  import('./features/decision/DecisionView.tsx').then((m) => ({ default: m.DecisionView }))
);

const AccuracyView = lazy(() =>
  import('./features/accuracy/AccuracyView.tsx').then((m) => ({ default: m.AccuracyView }))
);

const MethodologyDrawer = lazy(() =>
  import('./features/methodology/MethodologyDrawer.tsx').then((m) => ({ default: m.MethodologyDrawer }))
);

export function App() {
  const { state, updateState, stepDeliveryDay } = useUrlState();
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // 14-minute keep-alive heartbeat to prevent backend idle sleeping on free tiers
  useKeepAlive(14);

  // Direction tracking for view transition (-1: left, 1: right)
  const [direction, setDirection] = useState<number>(1);

  const handleSelectView = (newView: ViewTab) => {
    if (newView === state.view) return;
    if (state.view === 'decision' && newView === 'accuracy') {
      setDirection(1);
    } else if (state.view === 'accuracy' && newView === 'decision') {
      setDirection(-1);
    }
    updateState({ view: newView });
  };

  const handleDismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <LazyMotion features={domAnimation}>
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--color-bg)',
          color: 'var(--color-text-primary)',
        }}
      >
        {/* Global Control Room Header */}
        <Header
          activeView={state.view}
          onSelectView={handleSelectView}
          onOpenMethodology={() => setIsMethodologyOpen(true)}
        />

        {/* Global Control Bar with URL State Sync */}
        <ControlBar
          state={state}
          updateState={updateState}
          stepDeliveryDay={stepDeliveryDay}
        />

        {/* Main Content Area with Lazy-Loaded Views and Suspense */}
        <main
          style={{
            flex: 1,
            padding: 'var(--space-6)',
            maxWidth: '1600px',
            width: '100%',
            margin: '0 auto',
            position: 'relative',
          }}
        >
          <AnimatePresence mode="wait" custom={direction}>
            {state.view === 'decision' ? (
              <motion.div
                key="decision-view"
                custom={direction}
                variants={viewTransitionVariants}
                initial="enter"
                animate="center"
                exit="exit"
              >
                <Suspense fallback={<HeroChartSkeleton />}>
                  <DecisionView state={state} />
                </Suspense>
              </motion.div>
            ) : (
              <motion.div
                key="accuracy-view"
                custom={direction}
                variants={viewTransitionVariants}
                initial="enter"
                animate="center"
                exit="exit"
              >
                <Suspense fallback={<HeroChartSkeleton />}>
                  <AccuracyView
                    state={state}
                    onSelectDate={(date) => {
                      updateState({ deliveryDate: date, view: 'decision' });
                    }}
                  />
                </Suspense>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Slide-over Methodology Drawer */}
        <Suspense fallback={null}>
          <MethodologyDrawer
            isOpen={isMethodologyOpen}
            onClose={() => setIsMethodologyOpen(false)}
          />
        </Suspense>

        {/* Top-Right Notification Toasts */}
        <ToastContainer toasts={toasts} onDismiss={handleDismissToast} />
      </div>
    </LazyMotion>
  );
}

export default App;

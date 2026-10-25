import { useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, motion } from 'motion/react';
import { Header } from './components/Header.tsx';
import { ControlBar } from './components/ControlBar.tsx';
import { DecisionView } from './features/decision/DecisionView.tsx';
import { AccuracyView } from './features/accuracy/AccuracyView.tsx';
import { MethodologyDrawer } from './features/methodology/MethodologyDrawer.tsx';
import { ToastContainer } from './components/ui/ToastContainer.tsx';
import { useUrlState } from './hooks/useUrlState.ts';
import { viewTransitionVariants } from './design/motion.ts';
import type { ToastMessage, ViewTab } from './types.ts';

export function App() {
  const { state, updateState, stepDeliveryDay } = useUrlState();
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

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

        {/* Main Content Area with Direction-Aware Transitions */}
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
                <DecisionView state={state} />
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
                <AccuracyView
                  state={state}
                  onSelectDate={(date) => {
                    updateState({ deliveryDate: date, view: 'decision' });
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Slide-over Methodology Drawer */}
        <MethodologyDrawer
          isOpen={isMethodologyOpen}
          onClose={() => setIsMethodologyOpen(false)}
        />

        {/* Top-Right Notification Toasts */}
        <ToastContainer toasts={toasts} onDismiss={handleDismissToast} />
      </div>
    </LazyMotion>
  );
}

export default App;

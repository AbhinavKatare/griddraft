/**
 * Single source of truth for motion and animation tokens.
 * Adheres strictly to control-room ergonomics:
 * - Animate only transform and opacity.
 * - Reduced motion fallbacks for accessibility.
 * - Sub-350ms response to prevent blocking trader workflows.
 */

import type { Transition, Variants } from 'motion/react';

export const motionTokens = {
  duration: {
    micro: 0.12, // 120ms
    ui: 0.22,    // 220ms
    view: 0.35,  // 350ms
  },
  ease: {
    standard: [0.2, 0.0, 0.0, 1.0] as const,
    decelerate: [0.0, 0.0, 0.2, 1.0] as const,
    accelerate: [0.4, 0.0, 1.0, 1.0] as const,
  },
  spring: {
    control: {
      type: 'spring',
      stiffness: 380,
      damping: 32,
      mass: 0.9,
    } as Transition,
    bouncy: {
      type: 'spring',
      stiffness: 450,
      damping: 28,
    } as Transition,
  },
} as const;

/**
 * Direction-aware view transitions (Decision <-> Accuracy)
 */
export const viewTransitionVariants: Variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 16 : -16,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
    transition: {
      x: { duration: motionTokens.duration.view, ease: motionTokens.ease.decelerate },
      opacity: { duration: motionTokens.duration.view, ease: motionTokens.ease.decelerate },
    },
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -16 : 16,
    opacity: 0,
    transition: {
      x: { duration: motionTokens.duration.ui, ease: motionTokens.ease.accelerate },
      opacity: { duration: motionTokens.duration.ui, ease: motionTokens.ease.accelerate },
    },
  }),
};

/**
 * Slide-over drawer variants (Right-side on desktop, bottom sheet on mobile)
 */
export const drawerVariants: Variants = {
  hiddenRight: {
    x: '100%',
    opacity: 0.5,
    transition: { duration: motionTokens.duration.ui, ease: motionTokens.ease.accelerate },
  },
  visibleRight: {
    x: '0%',
    opacity: 1,
    transition: motionTokens.spring.control,
  },
  hiddenBottom: {
    y: '100%',
    opacity: 0.5,
    transition: { duration: motionTokens.duration.ui, ease: motionTokens.ease.accelerate },
  },
  visibleBottom: {
    y: '0%',
    opacity: 1,
    transition: motionTokens.spring.control,
  },
};

/**
 * Staggered container for card grids (40ms stagger)
 */
export const staggerContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04, // 40ms stagger
    },
  },
};

export const staggerItemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: motionTokens.duration.ui,
      ease: motionTokens.ease.decelerate,
    },
  },
};

/**
 * Fallback variant when prefers-reduced-motion is active
 */
export const reducedMotionVariants: Variants = {
  enter: { opacity: 0 },
  center: { opacity: 1, transition: { duration: motionTokens.duration.ui } },
  exit: { opacity: 0, transition: { duration: motionTokens.duration.micro } },
};

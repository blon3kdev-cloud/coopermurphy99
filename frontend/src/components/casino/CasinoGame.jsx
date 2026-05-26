import React, { useEffect, useRef } from 'react';
import '../category-page-header/CategoryPageHeader.css';
import '../../pages/casino-games.css';
import { createCryptoCasinoShell } from '../../casino/CryptoCasinoShell';

/**
 * Mounts a vanilla-JS casino game (keno / limbo / dice) into a React container.
 * Game modules are code-split — only the active game is downloaded.
 *
 * @param {{ gameType: 'keno' | 'limbo' | 'dice' | 'crash' | 'blackjack' | 'blitz', onBack: () => void }} props
 */
function CasinoGame({ gameType, onBack }) {
  const containerRef = useRef(null);
  const onBackRef = useRef(onBack);

  useEffect(() => {
    onBackRef.current = onBack;
  }, [onBack]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    let destroyed = false;
    let playRound = () => {};
    let shell = null;
    let gameApi = null;

    (async () => {
      const shellApi = createCryptoCasinoShell({
        onClose: () => onBackRef.current(),
        shellVariant: gameType,
        onPlay: () => playRound(),
      });
      if (destroyed) {
        shellApi.destroy();
        return;
      }
      shell = shellApi;

      if (gameType === 'keno') {
        const { mountKenoGame } = await import('../../casino/KenoGame');
        if (destroyed) return;
        const api = mountKenoGame({
          gameHost: shell.gameHost,
          shell: {
            el: shell.el,
            getBetAmount: shell.getBetAmount,
            getKenoDifficulty: shell.getKenoDifficulty,
            showResultModal: shell.showResultModal,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      } else if (gameType === 'limbo') {
        const { mountLimboGame } = await import('../../casino/LimboGame');
        if (destroyed) return;
        const api = mountLimboGame({
          gameHost: shell.gameHost,
          shell: {
            el: shell.el,
            getBetAmount: shell.getBetAmount,
            showResultModal: shell.showResultModal,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      } else if (gameType === 'crash') {
        const { mountCrashGame } = await import('../../casino/CrashGame');
        if (destroyed) return;
        const api = mountCrashGame({
          gameHost: shell.gameHost,
          shell: {
            el: shell.el,
            getBetAmount: shell.getBetAmount,
            showResultModal: shell.showResultModal,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      } else if (gameType === 'dice') {
        const { mountDiceGame } = await import('../../casino/DiceGame');
        if (destroyed) return;
        const api = mountDiceGame({
          gameHost: shell.gameHost,
          shell: {
            getBetAmount: shell.getBetAmount,
            onBetChange: shell.onBetChange,
            showResultModal: shell.showResultModal,
            updateProfit: shell.updateProfit,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      } else if (gameType === 'blackjack') {
        const { mountBlackjackGame } = await import('../../casino/BlackjackGame');
        if (destroyed) return;
        const api = mountBlackjackGame({
          gameHost: shell.gameHost,
          shell: {
            el: shell.el,
            getBetAmount: shell.getBetAmount,
            showResultModal: shell.showResultModal,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      } else if (gameType === 'blitz') {
        const { mountBlitzGame } = await import('../../casino/BlitzGame');
        if (destroyed) return;
        const api = mountBlitzGame({
          gameHost: shell.gameHost,
          shell: {
            el: shell.el,
            getBetAmount: shell.getBetAmount,
            onBetChange: shell.onBetChange,
            updateProfit: shell.updateProfit,
            showResultModal: shell.showResultModal,
            dismissResultModal: shell.dismissResultModal,
            setLoading: shell.setLoading,
            showGameError: shell.showGameError,
            clearGameError: shell.clearGameError,
          },
        });
        gameApi = api;
        playRound = api.playRound;
      }

      if (destroyed) {
        gameApi?.destroy?.();
        shell?.destroy();
        return;
      }
      container.appendChild(shell.el);
    })();

    return () => {
      destroyed = true;
      gameApi?.destroy?.();
      shell?.destroy();
      container.innerHTML = '';
    };
  }, [gameType]);

  return <div ref={containerRef} className="casino-game-container" />;
}

export default CasinoGame;

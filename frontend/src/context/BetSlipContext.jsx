import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
} from 'react';
import { isMarketOpenForBetting } from '../lib/marketFilters';
import { marketDisplayTitle } from '../lib/marketDisplay';

const BetSlipContext = createContext(null);
export const useBetSlip = () => useContext(BetSlipContext);

const INITIAL = { bets: [], isOpen: false, stake: '' };

function reducer(state, action) {
  switch (action.type) {
    case 'ADD': {
      const idx = state.bets.findIndex((b) => b.betId === action.bet.betId);
      if (idx >= 0 && state.bets[idx].selectedSide === action.bet.selectedSide) {
        const bets = state.bets.filter((_, i) => i !== idx);
        return {
          ...state,
          bets,
          isOpen: bets.length > 0 ? state.isOpen : false,
        };
      }
      const bets =
        idx >= 0
          ? state.bets.map((b, i) =>
              i === idx ? { ...b, selectedSide: action.bet.selectedSide } : b,
            )
          : [...state.bets, action.bet];
      return { ...state, bets, isOpen: true };
    }
    case 'REMOVE':
      return { ...state, bets: state.bets.filter((b) => b.betId !== action.betId) };
    case 'OPEN':
      return { ...state, isOpen: true };
    case 'CLOSE':
      return { ...state, isOpen: false };
    case 'SET_STAKE':
      return { ...state, stake: action.stake };
    case 'RESTORE':
      return {
        bets: action.bets,
        stake: action.stake ?? '',
        isOpen: action.isOpen ?? true,
      };
    default:
      return state;
  }
}

export function BetSlipProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  /** Add / update a regular market bet. Side defaults to 'yes'. */
  const addMarketBet = useCallback((market, side = 'yes') => {
    if (!isMarketOpenForBetting(market)) return;
    dispatch({
      type: 'ADD',
      bet: {
        betId: `market-${market.id}`,
        kind: 'market',
        image: market.image,
        title: marketDisplayTitle(market),
        date: market.date,
        yesLabel: market.yesLabel ?? 'Yes',
        noLabel: market.noLabel ?? 'No',
        yesOdds: market.yesOdds,
        noOdds: market.noOdds,
        selectedSide: side,
      },
    });
  }, []);

  /** Add / update a crypto bet. Side defaults to 'up'. */
  const addCryptoBet = useCallback((bet, side = 'up') => {
    dispatch({
      type: 'ADD',
      bet: {
        betId: `crypto-${bet.id}`,
        kind: 'crypto',
        symbol: bet.symbol,
        color: bet.color,
        title: bet.title,
        name: bet.name,
        selectedSide: side,
      },
    });
  }, []);

  const removeBet = useCallback(
    (betId) => dispatch({ type: 'REMOVE', betId }),
    [],
  );
  const open = useCallback(() => dispatch({ type: 'OPEN' }), []);
  const close = useCallback(() => dispatch({ type: 'CLOSE' }), []);
  const setStake = useCallback(
    (stake) => dispatch({ type: 'SET_STAKE', stake }),
    [],
  );

  const restoreSlip = useCallback((bets, stake, isOpen = true) => {
    dispatch({ type: 'RESTORE', bets, stake, isOpen });
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      addMarketBet,
      addCryptoBet,
      removeBet,
      open,
      close,
      setStake,
      restoreSlip,
    }),
    [state, addMarketBet, addCryptoBet, removeBet, open, close, setStake, restoreSlip],
  );

  return (
    <BetSlipContext.Provider value={value}>{children}</BetSlipContext.Provider>
  );
}

import { describe, expect, it } from 'vitest';
import {
  AREAS,
  AREA_INFO,
  areaDoTipo,
  entregaDoTipo,
  normalizarClassificacao,
  normalizarTipo,
  parseArea,
  rotuloClassificacao,
  tipoInfo,
} from './categorias';

describe('normalizarTipo', () => {
  it('faz trim + lowercase', () => {
    expect(normalizarTipo('  Fisico ')).toBe('fisico');
    expect(normalizarTipo('GAME')).toBe('game');
  });
  it('trata null/undefined/nao-string como vazio', () => {
    expect(normalizarTipo(null)).toBe('');
    expect(normalizarTipo(undefined)).toBe('');
    expect(normalizarTipo(42)).toBe('');
  });
});

describe('areaDoTipo', () => {
  it.each([
    ['ebook', 'digitais'],
    ['fisico', 'fisicos'],
    ['game', 'aplicativos'],
    ['app', 'aplicativos'],
    ['assinatura', 'aplicativos'],
  ])('%s -> %s', (tipo, area) => {
    expect(areaDoTipo(tipo)).toBe(area);
  });

  it('normaliza antes de comparar', () => {
    expect(areaDoTipo(' FISICO ')).toBe('fisicos');
    expect(areaDoTipo('Assinatura')).toBe('aplicativos');
  });

  it('qualquer valor desconhecido, vazio ou nulo cai em digitais', () => {
    expect(areaDoTipo('digital')).toBe('digitais');
    expect(areaDoTipo('')).toBe('digitais');
    expect(areaDoTipo('   ')).toBe('digitais');
    expect(areaDoTipo(null)).toBe('digitais');
    expect(areaDoTipo(undefined)).toBe('digitais');
    expect(areaDoTipo('qualquer-coisa')).toBe('digitais');
  });
});

describe('parseArea', () => {
  it('aceita as tres areas e ignora o resto', () => {
    for (const a of AREAS) expect(parseArea(a)).toBe(a);
    expect(parseArea('DIGITAIS')).toBe('digitais');
    expect(parseArea('outra')).toBeNull();
    expect(parseArea(null)).toBeNull();
    expect(parseArea('')).toBeNull();
  });
});

describe('rotulos e icones', () => {
  it('toda area tem rotulo e icone', () => {
    for (const a of AREAS) {
      expect(AREA_INFO[a].label.length).toBeGreaterThan(0);
      expect(AREA_INFO[a].icon).toBeTruthy();
    }
  });
  it('tipoInfo devolve rotulo conhecido ou "Digital"', () => {
    expect(tipoInfo('fisico').label).toBe('Físico');
    expect(tipoInfo('game').label).toBe('Game');
    expect(tipoInfo('app').area).toBe('aplicativos');
    expect(tipoInfo('xyz').label).toBe('Digital');
    expect(tipoInfo('xyz').area).toBe('digitais');
    expect(tipoInfo(undefined).tipo).toBe('ebook');
  });
});

describe('entregaDoTipo', () => {
  it('segue as regras de entrega do negocio', () => {
    expect(entregaDoTipo('ebook')).toBe('email-link');
    expect(entregaDoTipo('app')).toBe('email-licenca');
    expect(entregaDoTipo('assinatura')).toBe('email-licenca');
    expect(entregaDoTipo('fisico')).toBe('frete');
  });
});

describe('classificacao', () => {
  it('normaliza variacoes e cai em L', () => {
    expect(normalizarClassificacao('12')).toBe('12');
    expect(normalizarClassificacao(' 18+ ')).toBe('18');
    expect(normalizarClassificacao('l')).toBe('L');
    expect(normalizarClassificacao('99')).toBe('L');
    expect(normalizarClassificacao(null)).toBe('L');
    expect(normalizarClassificacao(16)).toBe('16');
  });
  it('rotulo: L ou N+', () => {
    expect(rotuloClassificacao('L')).toBe('L');
    expect(rotuloClassificacao('14')).toBe('14+');
  });
});

// Pesos mexicanos sin centavos: "MX$60,000".
const PESOS = new Intl.NumberFormat("en-US", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
export const pesos = (n) => PESOS.format(n);

// Número con hasta 2 decimales y sin ceros de más: 3.06, 5.
export const numero = (n) => Number(n.toFixed(2)).toLocaleString("en-US");

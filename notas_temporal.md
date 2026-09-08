# Notas — Implementación plano temporal

## Problema: Movimientos simultáneos dependientes

### Descripción:
En un plano en un tiempo k, dos agentes i_1, i_2 pueden realizar movimientos en donde i_1 termine en la posición de i_2 en el k y i_2 termine en una posición diferente a la posición de i_1 en k, es decir:
$$
\rho^{i_1}_{a,b,k} 
\land
\rho^{i_2}_{b,c,k}
$$
Donde $c \neq a \neq b$. Es un par de movimientos válido.

### Posible solución:
Implementar un algoritmo que:
1. Agrupe movimientos que comparten alguna posición
2. En los grupos de posiciones compartidas, ordene los movimientos de forma que se liberen posiciones de salida de las que dependan posiciones de llegada

### A tener en cuenta:
La condición &c \neq a \neq b& puede pasarse por algo en la implementación fácilmente.
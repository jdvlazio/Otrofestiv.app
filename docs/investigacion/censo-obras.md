# Censo de obras publicadas — festivals/*.json

Fecha: 2026-10-12 · repo clon7 (rama rev/ficma-main) · 32 festivales: aff-2026, biff-2026, cineautopsia-2026, cinemancia-2025, cinemancia-2026, fantasmagoria-2026, fantasofest-2026, ficcali-2026, ficci-65, ficdeh-2026, ficma-2026, ficmontanas-2026, ficpa-2026, filcmar-2026, finca-2026, girardota-2026, itagui-2026, jardin-2026, leviza-2026, mamut-2026, midbo-2026, mubibogota-2026, narrarelfuturo-2026, olhar-2026, popayan-2026, qaff-2026, siembrafest-2026, tercertiempo-2026, tiff-2026, tribeca-2026, vartex-2026, villadelcine-2026

Método: se recorren `films[]` de cada JSON y los `film_list[]` de los programas; se ignoran `type=="event"`. Clave de obra única: `tmdb_id` si existe; si no, `norm(title)|norm(director)` (lib.norm: minúsculas, sin tildes, solo alfanumérico). Un «registro» es cada aparición (una obra con 3 funciones en un festival = 3 registros).

## 1. Totales

- Registros de obra: **4490** (de los cuales 1802 viven dentro de `film_list` de programas; 2688 son entradas de primer nivel)
- Obras únicas (tmdb_id o título+director): **2571**
  - agrupadas por tmdb_id: 920
  - agrupadas por título+director (sin tmdb_id): 1651
- Registros por festival: aff-2026=39, biff-2026=205, cineautopsia-2026=78, cinemancia-2025=186, cinemancia-2026=219, fantasmagoria-2026=122, fantasofest-2026=31, ficcali-2026=110, ficci-65=338, ficdeh-2026=417, ficma-2026=69, ficmontanas-2026=93, ficpa-2026=84, filcmar-2026=45, finca-2026=40, girardota-2026=47, itagui-2026=31, jardin-2026=71, leviza-2026=40, mamut-2026=56, midbo-2026=141, mubibogota-2026=12, narrarelfuturo-2026=53, olhar-2026=102, popayan-2026=144, qaff-2026=92, siembrafest-2026=116, tercertiempo-2026=48, tiff-2026=1041, tribeca-2026=256, vartex-2026=37, villadelcine-2026=127

## 2. Obras en 2 o más festivales

- Obras únicas presentes en ≥2 festivales: **125** (4.9% del catálogo único)
- Distribución: 2 festivales → 93 obras, 3 festivales → 24 obras, 4 festivales → 6 obras, 5 festivales → 2 obras

### Las 30 más repetidas

| # | Obra (director) | Festivales | clave |
|---|---|---|---|
| 1 | CHAIKA (Ingrid Paola Bonilla Rodriguez) | 5: cineautopsia-2026, fantasmagoria-2026, ficpa-2026, narrarelfuturo-2026, popayan-2026 | tmdb:1689999 |
| 2 | Decaer (Juan Camilo González) | 5: cineautopsia-2026, cinemancia-2026, mamut-2026, midbo-2026, popayan-2026 | tmdb:1668881 |
| 3 | El hogar fue sepultado en esa tierra que nunca pudimos encontrar (Deimer Quintero Vertel) | 4: cinemancia-2026, ficma-2026, mamut-2026, midbo-2026 | tmdb:1663181 |
| 4 | Llueve sobre Babel (Gala del Sol) | 4: ficma-2026, girardota-2026, narrarelfuturo-2026, villadelcine-2026 | tmdb:1388977 |
| 5 | Madres de Nacimiento (Gloria Isabel Gómez) | 4: cinemancia-2026, jardin-2026, midbo-2026, popayan-2026 | tmdb:1668902 |
| 6 | Pudor ante el asalto de los ojos furtivos (Laura María Rdríguez) | 4: cineautopsia-2026, fantasmagoria-2026, filcmar-2026, popayan-2026 | tmdb:1592968 |
| 7 | Refracción (Isabella Palacio) | 4: cinemancia-2026, girardota-2026, jardin-2026, narrarelfuturo-2026 | tmdb:1584776 |
| 8 | Relatos del camino (Daniel Prieto Muriel) | 4: ficmontanas-2026, ficpa-2026, jardin-2026, siembrafest-2026 | td:relatos del camino|daniel prieto muriel |
| 9 | Akababuru: Expresión de Asombro (Irati Dojura Landa Yagarí) | 3: ficcali-2026, ficpa-2026, popayan-2026 | tmdb:1418533 |
| 10 | Andariega (Raúl Soto Rodríguez) | 3: ficma-2026, filcmar-2026, siembrafest-2026 | tmdb:1456127 |
| 11 | Borrachos Mientras Escuchamos las Gotas Caer (Santiago Gómez Ramírez) | 3: biff-2026, cinemancia-2026, villadelcine-2026 | tmdb:1743109 |
| 12 | Cobarde (Lukas Dhont) | 3: biff-2026, mubibogota-2026, tiff-2026 | tmdb:1437981 |
| 13 | Elementales (Camilo Botero Jaramillo) | 3: girardota-2026, jardin-2026, siembrafest-2026 | td:elementales|camilo botero jaramillo |
| 14 | Filme Pin (María Rojas Arias, Andrés Jurado) | 3: cineautopsia-2026, midbo-2026, popayan-2026 | tmdb:1616856 |
| 15 | Habitante (José Alejandro González) | 3: ficma-2026, itagui-2026, narrarelfuturo-2026 | tmdb:1571285 |
| 16 | La Bola Negra (Javier Calvo, Javier Ambrossi) | 3: biff-2026, ficcali-2026, tiff-2026 | tmdb:1422041 |
| 17 | La Libertad Doble (Lisandro Alonso) | 3: biff-2026, ficcali-2026, tiff-2026 | tmdb:1387981 |
| 18 | La Mona (Laura Gutiérrez Ardila) | 3: jardin-2026, popayan-2026, villadelcine-2026 | tmdb:1444298 |
| 19 | La gran hazaña (Luber Yesid Zúñiga Ordóñez) | 3: ficdeh-2026, ficmontanas-2026, siembrafest-2026 | td:la gran hazana|luber yesid zuniga ordone |
| 20 | Lolita en Honda (Daniel Torres) | 3: cinemancia-2026, mamut-2026, midbo-2026 | tmdb:1665546 |
| 21 | Los Años del Conejo (Raquel Tamayo Gutiérrez) | 3: cineautopsia-2026, girardota-2026, jardin-2026 | tmdb:1617929 |
| 22 | Minotauro (Andrey Zvyagintsev) | 3: biff-2026, ficcali-2026, tiff-2026 | tmdb:848700 |
| 23 | Mu-Ki-Ra (Estefania Piñeres) | 3: fantasmagoria-2026, ficcali-2026, filcmar-2026 | tmdb:1446898 |
| 24 | Para No Volver (Tania Galvis) | 3: biff-2026, cinemancia-2026, filcmar-2026 | tmdb:1743118 |
| 25 | Que El Cielo Nos Perdone (Andrés Buitrago) | 3: fantasmagoria-2026, ficma-2026, villadelcine-2026 | tmdb:1565878 |
| 26 | Sol de niebla (Maria José Ibarra, Florentino Vargas) | 3: filcmar-2026, mamut-2026, midbo-2026 | tmdb:1791609 |
| 27 | Sombras en la niebla (Pedro Pablo Vega) | 3: cinemancia-2026, midbo-2026, popayan-2026 | tmdb:1668876 |
| 28 | Somnolítico (Abril Natalia Velázquez) | 3: ficcali-2026, filcmar-2026, jardin-2026 | tmdb:1590709 |
| 29 | Soñé su nombre (Ángela Carabalí) | 3: ficdeh-2026, qaff-2026, siembrafest-2026 | td:sone su nombre|angela carabali |
| 30 | Soñé su nombre (Ángela Carabalí) | 3: ficma-2026, jardin-2026, narrarelfuturo-2026 | tmdb:1454365 |

## 3. Contradicciones entre festivales (obras repetidas)

- Obras repetidas con al menos un campo contradictorio: **111** de 125
- Por campo: poster=107, synopsis=84, director=27, year=24, duration=9
  - Nota: `poster` distinto incluye el caso frecuente de rutas `/assets/<festival>/…` propias de cada festival aunque la imagen sea la misma; `synopsis` distinta incluye variantes de redacción/longitud.

### 20 ejemplos concretos

**Somnolítico** — `tmdb:1590709`
- director:
  - ficcali-2026: Abril Natalia Velázquez
  - filcmar-2026: Abril Natalia Velásquez
  - jardin-2026: Abril Velasquez
- year:
  - ficcali-2026: 2026
  - filcmar-2026: 2026
  - jardin-2026: 2025
- poster:
  - ficcali-2026: /assets/ficcali-2026/somnolitico.jpg
  - filcmar-2026: /assets/filcmar-2026/somnolitico.jpg
  - jardin-2026: /assets/jardin-2026/somnolitico.jpg
- synopsis:
  - ficcali-2026: Un ser extraño pierde su rumbo en el caos del sistema de transporte, desplazándose de un l…
  - filcmar-2026: Un ser extraño se pierde en el caos del sistema de transporte, moviéndose de un lugar a ot…
  - jardin-2026: Un ser extraño pierde su rumbo en el caos del sistema de transporte, pasando de un lugar a…

**Llueve sobre Babel** — `tmdb:1388977`
- year:
  - ficma-2026: 2025
  - girardota-2026: 2025
  - narrarelfuturo-2026: 2026
  - villadelcine-2026: 2026
- duration:
  - ficma-2026: 111 min
  - girardota-2026: 111 min
  - narrarelfuturo-2026: 113 min
  - villadelcine-2026: 120 min
- poster:
  - ficma-2026: /assets/ficma/llueve-sobre-babel.jpg
  - girardota-2026: /assets/girardota-2026/llueve-sobre-babel.jpg
  - narrarelfuturo-2026: /assets/narrarelfuturo-2026/llueve-sobre-babel.jpg
  - villadelcine-2026: /assets/villadelcine-2026/llueve-sobre-babel.jpg
- synopsis:
  - ficma-2026: En el bar Babel, donde vivos y muertos se mezclan, Dante busca recordar su pasado antes de…
  - girardota-2026: En el bar Babel, donde vivos y muertos se mezclan, Dante busca recordar su pasado antes de…
  - narrarelfuturo-2026: El limbo nunca fue tan seductor como en Llueve sobre Babel. Escrita y dirigida por Gala de…
  - villadelcine-2026: Esta reinterpretación del Inferno de Dante toma la forma de un drama coral. La acción se c…

**Brigitte, Planeta B** — `tmdb:1498786`
- year:
  - aff-2026: 2025
  - ficma-2026: 2026
- poster:
  - aff-2026: https://image.tmdb.org/t/p/w500/ajUS8Zl4qCGcsuX9lNgphTYh3Qp.jpg
  - ficma-2026: /assets/ficma/brigitte-planeta-b.jpg
- synopsis:
  - aff-2026: Brigitte Baptiste, Ph.D., se ha consolidado como una de las principales expertas ambiental…
  - ficma-2026: Brigitte Baptiste is a female transgender ecologist whose groundbreaking research has chal…

**The Man I Love** — `tmdb:1458914`
- year:
  - biff-2026: 2026
  - tiff-2026: 2027
- poster:
  - biff-2026: /assets/biff-2026/the-man-i-love.jpg
  - tiff-2026: https://image.tmdb.org/t/p/w500/qIZ8pQ5nQjRKDtmsl0DYGO1nCQ.jpg
- synopsis:
  - biff-2026: Finales de la década de 1980 en New York. Jimmy George, un carismático artista del Downtow…
  - tiff-2026: La mirada de Ira Sachs sobre unos artistas neoyorquinos que viven bajo el fantasma del sid…

**Everytime** — `tmdb:1655419`
- duration:
  - biff-2026: 124 min
  - tiff-2026: 119 min
- poster:
  - biff-2026: /assets/biff-2026/everytime.jpg
  - tiff-2026: https://image.tmdb.org/t/p/w500/lByDG8HfSamsJqFLcvW9dlxBxIA.jpg
- synopsis:
  - biff-2026: Una tragedia une a una madre, a su hija y a un chico adolescente. Mientras luchan con los …
  - tiff-2026: Una madre en duelo y el novio de su hija muerta indagan en la culpa, el duelo y el perdón …

**Para No Volver** — `tmdb:1743118`
- year:
  - biff-2026: 2025
  - cinemancia-2026: 2026
  - filcmar-2026: 2026
- poster:
  - biff-2026: /assets/biff-2026/para-no-volver.jpg
  - cinemancia-2026: https://image.tmdb.org/t/p/w500/k2RvfqR0QSL4D5PzFkkomzRZJ8q.jpg
  - filcmar-2026: /assets/filcmar-2026/para-no-volver.jpg
- synopsis:
  - biff-2026: Cuando Karina se entera de que está embarazada del bebé de Charlie, ella y su mejor amiga …
  - cinemancia-2026: Cuando Karina se entera de que está embarazada del bebé de Charlie, ella y su mejor amiga …
  - filcmar-2026: Cuando Karina descubre que está embarazada del bebé de Charlie, ella y su mejor amiga Eli …

**Borrachos Mientras Escuchamos las Gotas Caer** — `tmdb:1743109`
- director:
  - biff-2026: Santiago Gómez Ramírez
  - cinemancia-2026: Santiago Gómez Ramírez
  - villadelcine-2026: Santiago Gómez
- poster:
  - biff-2026: /assets/biff-2026/borrachos-mientras-escuchamos-las-gotas-caer.jpg
  - cinemancia-2026: https://image.tmdb.org/t/p/w500/3R73xUlBIBGXY5q8i9HZYLEidLy.jpg
  - villadelcine-2026: /assets/villadelcine-2026/drunk-hearing-the-rain-drops-fall.jpg
- synopsis:
  - biff-2026: Retrata la historia de León Ramírez e Isabel Velásquez, dos ancianos de casi 90 años que a…
  - cinemancia-2026: Retrata la historia de León Ramírez e Isabel Velásquez, dos ancianos de casi 90 años que a…
  - villadelcine-2026: En la vejez, una pareja contempla cómo la tierra destinada a sostener su retiro se convier…

**6 Meses en el Edificio Rosa con Azul** — `tmdb:1025407`
- director:
  - biff-2026: Bruno Santamaría Razo
  - ficcali-2026: Bruno Santamaría
- poster:
  - biff-2026: /assets/biff-2026/6-meses-en-el-edificio-rosa-con-azul.jpg
  - ficcali-2026: /assets/ficcali-2026/seis-meses-en-el-edificio-rosa-con-azul.jpg
- synopsis:
  - biff-2026: Ciudad de México, principios de los 90. El día que Bruno cumple 11 años, los sentimientos …
  - ficcali-2026: Ciudad de México, principio de los años noventa. El día que Bruno cumple once años, se ena…

**Princesa Burro** — `tmdb:1536431`
- director:
  - biff-2026: Cristóbal León, Joaquín Cociña
  - ficcali-2026: Joaquín Cociña, Cristóbal León
- poster:
  - biff-2026: /assets/biff-2026/princesa-burro.jpg
  - ficcali-2026: /assets/ficcali-2026/princesa-burro.jpg
- synopsis:
  - biff-2026: En un reino de cuento de hadas donde el amor está prohibido, la princesa Diana desafía el …
  - ficcali-2026: En un reino de cuento de hadas, donde el amor está prohibido, la princesa Diana desafía el…

**El Despertar** — `tmdb:1657630`
- director:
  - biff-2026: Jaime Osorio Márquez
  - fantasmagoria-2026: Jaime Osorio Marquez, Federico Durán y José Luis Rugeles
- poster:
  - biff-2026: /assets/biff-2026/el-despertar.jpg
  - fantasmagoria-2026: /assets/fantasmagoria-2026/el-despertar.jpg
- synopsis:
  - biff-2026: En lo más profundo de la selva una unidad militar de élite entra en territorio desconocido…
  - fantasmagoria-2026: En lo más profundo de la selva amazónica, una unidad militar de élite es enviada a elimina…

**Minotauro** — `tmdb:848700`
- duration:
  - biff-2026: 141 min
  - ficcali-2026: 135 min
  - tiff-2026: 140 min
- poster:
  - biff-2026: /assets/biff-2026/minotauro.jpg
  - ficcali-2026: /assets/ficcali-2026/minotauro.jpg
  - tiff-2026: https://image.tmdb.org/t/p/w500/7XH2vaVsishBS0GuCgO3bOXfCaB.jpg
- synopsis:
  - biff-2026: Rusia, 2022. Cuando Gleb, un exitoso director de empresa, se ve acorralado por las crecien…
  - ficcali-2026: Es la contemplación del director sobre la naturaleza de las relaciones humanas, el estado …
  - tiff-2026: Tras nueve años de silencio, durante los cuales huyó de su Rusia natal al exilio, Andrey Z…

**Cobarde** — `tmdb:1437981`
- duration:
  - biff-2026: 125 min
  - mubibogota-2026: 120 min
  - tiff-2026: 120 min
- poster:
  - biff-2026: /assets/biff-2026/cobarde.jpg
  - mubibogota-2026: /assets/mubibogota-2026/cobarde.jpg
  - tiff-2026: https://image.tmdb.org/t/p/w500/A3y7oED7yQ1WIxJIl9jey9Ls0aU.jpg
- synopsis:
  - biff-2026: A medida que la Primera Guerra Mundial se prolonga, Pierre, un soldado recién llegado al f…
  - mubibogota-2026: Pierre llega al frente de batalla como un joven soldado deseoso de encontrar su lugar en u…
  - tiff-2026: El conmovedor tercer largometraje del director belga Lukas Dhont celebra un amor que flore…

**Hermanas** — `tmdb:1556887`
- director:
  - biff-2026: Ione Hernández Sáenz
  - tiff-2026: Ione Hernández
- poster:
  - biff-2026: /assets/biff-2026/hermanas.jpg
  - tiff-2026: https://images.ctfassets.net/22n7d68fswlw/6ZVzJDgqYNfz8yA7SdLXag/6df15fc8227651d9aaac01cfb85e642f/Sisters-01.jpg
- synopsis:
  - biff-2026: Chelo y Marta son hermanas, y sus vidas están a punto de cambiar para siempre. Ese verano,…
  - tiff-2026: En las afueras de Madrid, dos hermanas reúnen a sus familias un fin de semana de verano pa…

**Iluminada** — `tmdb:1000097`
- director:
  - biff-2026: Nicolás Rincón Gille
  - ficcali-2026: Nicolás Rincón
- poster:
  - biff-2026: /assets/biff-2026/iluminada.jpg
  - ficcali-2026: /assets/ficcali-2026/iluminada.jpg
- synopsis:
  - biff-2026: Iluminada tiene visiones. Intenta comprenderlas escribiendo en diarios privados. Sus escri…
  - ficcali-2026: Iluminada tiene visiones que trata de entender escribiendo diarios íntimos. Sus textos son…

**CHAIKA** — `tmdb:1689999`
- director:
  - cineautopsia-2026: Ingrid Paola Bonilla Rodriguez
  - fantasmagoria-2026: Ingrid Bonilla Rodríguez
  - ficpa-2026: Ingrid Paola Bonilla Rodríguez
  - narrarelfuturo-2026: Ingrid Paola Bonilla Rodriguez
  - popayan-2026: Ingrid Paola Bonilla Rodríguez
- poster:
  - cineautopsia-2026: /assets/cineautopsia/chaika.jpg
  - fantasmagoria-2026: /assets/fantasmagoria-2026/chaika.jpg
  - ficpa-2026: /assets/ficpa-2026/chaika.jpg
  - narrarelfuturo-2026: /assets/narrarelfuturo-2026/chaika.jpg
  - popayan-2026: /assets/popayan-2026/chaika.jpg
- synopsis:
  - cineautopsia-2026: Valentina, una cosmonauta rusa de 76 años, recibe una carta enviada desde Cuba con treinta…
  - fantasmagoria-2026: Valentina, una cosmonauta rusa de 76 años, llega a una Cuba ucrónica y nebulosa tras recib…
  - ficpa-2026: Valentina, una cosmonauta rusa de 76 años, llega a una Cuba ucrónica y nebulosa tras recib…
  - narrarelfuturo-2026: Valentina, una cosmonauta rusa de 76 años, recibe una carta enviada desde Cuba con treinta…
  - popayan-2026: Valentina, una cosmonauta rusa de 76 años, recibe una carta enviada desde Cuba con treinta…

**Filme Pin** — `tmdb:1616856`
- director:
  - cineautopsia-2026: María Rojas Arias, Andrés Jurado
  - midbo-2026: María Rojas Arias y Andrés Jurado
  - popayan-2026: Maria Rojas Arias y Andrés Jurado
- poster:
  - cineautopsia-2026: /assets/cineautopsia/filme-pin.jpg
  - midbo-2026: /assets/midbo-2026/filme-pin.jpg
  - popayan-2026: /assets/popayan-2026/filme-pin.jpg
- synopsis:
  - cineautopsia-2026: Entre luz, metal y plata, Filme Pin transforma una colección de pines solidarios en un arc…
  - midbo-2026: Entre la luz, el metal y la plata, «Filme Pin» convierte una colección de pines de solidar…
  - popayan-2026: Entre luz, metal y destellos, Filme PIN reimagina un archivo, redimensiona el objeto popul…

**Cartas a mis padres muertos** — `td:cartas a mis padres muertos|ignacio aguero`
- duration:
  - cinemancia-2025: 106 min
  - olhar-2026: 124 min
- poster:
  - cinemancia-2025: https://image.tmdb.org/t/p/w500/6zAG96fKKqm4QmYANLmXpVLa9JQ.jpg
  - olhar-2026: /6zAG96fKKqm4QmYANLmXpVLa9JQ.jpg
- synopsis:
  - cinemancia-2025: Ignacio Agüero realiza un viaje íntimo a través de las cartas de sus padres muertos, const…
  - olhar-2026: Raúl Ruiz, cineasta chileno como Ignacio Agüero, escreveu em seu texto Para um Cinema Xamâ…

**Trizas** — `tmdb:1604094`
- director:
  - cinemancia-2026: Luciana Decker
  - midbo-2026: Luciana Decker Orozco
- poster:
  - cinemancia-2026: https://image.tmdb.org/t/p/w500/6561nDr66xGl3MFVSMsVqGEKtn.jpg
  - midbo-2026: /assets/midbo-2026/trizas.jpg
- synopsis:
  - cinemancia-2026: Dos viajes se cruzan de forma anacrónica: el de un médico inglés en Bolivia en los años tr…
  - midbo-2026: Dos viajes se entrelazan anacrónicamente: el de un médico inglés en Bolivia durante la déc…

**Futuros luminosos** — `tmdb:1603950`
- director:
  - cinemancia-2026: Ismael García
  - jardin-2026: Ismael García Ramírez
- poster:
  - cinemancia-2026: https://image.tmdb.org/t/p/w500/dcrtvU52NOn6HTHJHC8ZyX8ySsJ.jpg
  - jardin-2026: /assets/jardin-2026/futuros-luminosos.jpg
- synopsis:
  - cinemancia-2026: En un lugar extraño y oscuro, un grupo de jóvenes de colores proyecta su futuro.…
  - jardin-2026: Simón (13) vive en un pueblo abandonado, allí pasa una última noche junto a su hermana Sol…

**Las almas ni los ojos** — `tmdb:1665538`
- director:
  - cinemancia-2026: Canela Reyes y César Jaimes
  - midbo-2026: Cesar Jaimes y Canela Reyes
- poster:
  - cinemancia-2026: https://image.tmdb.org/t/p/w500/1qEi6ZaKPyVOEilZYdRdMK4MVJj.jpg
  - midbo-2026: /assets/midbo-2026/las-almas-ni-los-ojos.jpg
- synopsis:
  - cinemancia-2026: Tras huir de la violencia a los 15 años, Pacho pasa cuatro décadas lejos de Anserma. Ahora…
  - midbo-2026: Pacho salió de su pueblo por hechos violentos hace más de 50 años y nunca pudo regresar. A…

## 4. Cobertura por campo

| Campo | registros con dato | % registros | obras únicas con dato (algún registro) | % únicas |
|---|---|---|---|---|
| tmdb_id | 1975 | 44.0% | 920 | 35.8% |
| poster | 3900 | 86.9% | 2093 | 81.4% |
| synopsis | 3447 | 76.8% | 1803 | 70.1% |
| synopsis_en | 2989 | 66.6% | 1468 | 57.1% |
| year | 3458 | 77.0% | 1798 | 69.9% |
| duration | 4301 | 95.8% | 2419 | 94.1% |
| country | 4328 | 96.4% | 2432 | 94.6% |
| director | 3883 | 86.5% | 2114 | 82.2% |
| lbSlug | 2756 | 61.4% | 1277 | 49.7% |

## 5. Obras sin tmdb_id

- Registros sin tmdb_id: **2515** de 4490 (56.0%)
- Obras únicas sin tmdb_id (candidatas a id propio): **1651** de 2571 (64.2%)
  - de ellas, sin director (clave solo por título): 456
  - de ellas, en ≥2 festivales: 38
  - títulos normalizados que caen en más de una clave (posibles duplicados por director distinto o tmdb_id vs sin tmdb_id): 127
    - «abortion party»: td:abortion party| / tmdb:1512855
    - «acto de ver»: td:acto de ver|jean paul sanchez florez / tmdb:1547380
    - «agua fria»: td:agua fria| / tmdb:1562451
    - «akababuru expresion de asombro»: td:akababuru expresion de asombro|irati doj / tmdb:1418533
    - «an incomplete calendar»: td:an incomplete calendar| / td:an incomplete calendar|sanaz sohrabi / tmdb:1633334
    - «andariega»: td:andariega|raul soto / tmdb:1456127
    - «apotnojushi la casa del viento»: td:apotnojushi la casa del viento| / td:apotnojushi la casa del viento|marbel in / tmdb:1668905
    - «balada de peces y pajaros»: td:balada de peces y pajaros|anny uribe jua / tmdb:1592956
    - «belleza letal»: td:belleza letal| / td:belleza letal|ron marquez andres felipe 
    - «bojaya la verdad desde adentro»: td:bojaya la verdad desde adentro|ramon ale / tmdb:1738325
    - «bosque arriba en la montana»: td:bosque arriba en la montana|sofia borden / tmdb:1616844
    - «buddies»: td:buddies|fraser wolfe / tmdb:259433
    - «caida libre»: td:caida libre| / td:caida libre|wilson borja
    - «carola»: td:carola|violeta barrios ramirez / tmdb:1497688
    - «carrie»: td:carrie|mike flanagan / tmdb:7340
    - «cartas a mis padres muertos»: td:cartas a mis padres muertos|ignacio ague / tmdb:1493026
    - «cayenas libertarias»: td:cayenas libertarias|javier camilo arangu / tmdb:1737961
    - «chaika»: td:chaika|ingrid bonilla rodriguez / tmdb:1689999
    - «chicha la chicharra»: td:chicha la chicharra|sofia alejandra uzca / tmdb:1483504
    - «colors of white rock»: td:colors of white rock|khoroldorj choijoov / tmdb:874510
    - «como todo mortal»: td:como todo mortal|maria molina peiro / tmdb:1651710
    - «corazon galvanico»: td:corazon galvanico|valentina valencia / tmdb:1376037
    - «crocodile»: td:crocodile|peter faiman / td:crocodile|the critics and pietra brettke
    - «de saul»: td:de saul|santiago gomxz / td:de saul|santiago gomxz cristian rojas
    - «decaer»: td:decaer| / tmdb:1668881

## 6. Sidecars de decisiones (festivals/staging)

### *-correcciones.json — 15 archivos, 138 entradas en total
- biff-2026-correcciones: 1
- fantasmagoria-2026-correcciones: 11
- ficcali-2026-correcciones: 23
- ficma-2026-ig-correcciones: 19
- ficpa-2026-correcciones: 5
- filcmar-2026-correcciones: 8
- girardota-2026-correcciones: 1
- itagui-2026-correcciones: 4
- jardin-2026-correcciones: 3
- mamut-2026-correcciones: 7
- mamut-2026-programa-correcciones: 2
- midbo-2026-correcciones: 21
- mubibogota-2026-correcciones: 3
- popayan-2026-correcciones: 7
- villadelcine-2026-correcciones: 23
- Títulos de estos sidecars que corresponden a obras en ≥2 festivales: **10**
  - el mundo de humberto
  - la bola negra
  - la libertad doble
  - minotauro
  - no es el fin del mundo
  - quazar
  - sol de niebla
  - somnolitico
  - the travelers
  - tuktu padre maiz

### *-sinopsis.json — 7 archivos, 45 entradas en total
- biff-2026-sinopsis: 2
- fantasmagoria-2026-sinopsis: 16
- ficcali-2026-sinopsis: 9
- ficpa-2026-sinopsis: 5
- filcmar-2026-sinopsis: 1
- mamut-2026-sinopsis: 7
- popayan-2026-sinopsis: 5
- Títulos de estos sidecars que corresponden a obras en ≥2 festivales: **4**
  - la habitacion del macho cabrio
  - no menguara el fuego de esta luna
  - sirenas en la niebla
  - una vez en un cuerpo

### *-afiches.json — 8 archivos, 183 entradas en total
- biff-2026-afiches: 1
- fantasmagoria-2026-afiches: 9
- ficcali-2026-afiches: 75
- filcmar-2026-afiches: 37
- girardota-2026-afiches: 17
- mamut-2026-afiches: 2
- midbo-2026-afiches: 23
- popayan-2026-afiches: 19
- Títulos de estos sidecars que corresponden a obras en ≥2 festivales: **44**
  - aguapanela
  - alivios
  - andariega
  - aquileo venganza
  - bertha
  - chaika
  - despues de tanto amor
  - ecrire la vie annie ernaux racontee par des lyceennes et des lyceens
  - el cazador
  - el mundo de humberto
  - en todo y en nada
  - filme pin
  - futuros luminosos
  - hdlt
  - iluminada
  - la corazonada
  - la gran hazana
  - la mansion de araucaima
  - la mona
  - la paga
  - la pecera
  - la rebelion de un fantasma
  - lo demas es ruido
  - los anos del conejo
  - luis tercero
  - mu ki ra
  - no es el fin del mundo
  - no menguara el fuego de esta luna
  - notre corps
  - nuestro cuerpo es una estrella que se expande
  - para no volver
  - princesa burro
  - pudor ante el asalto de los ojos furtivos
  - quazar
  - refraccion
  - relicto
  - seis meses en el edificio rosa con azul
  - siempre soy tu animal materno
  - sol de niebla
  - somnolitico
  - the travelers
  - tuktu padre maiz
  - una vez en un cuerpo
  - ya se ven los tigres en la lluvia


### Notas al punto 6
- `ficma-2026-ig-correcciones.json` NO es un sidecar de fichas: es la lista `ok` de 19 avisos de láminas de IG (horas/erratas), sin títulos como clave. Descontándolo, las correcciones de fichas son **119 entradas en 14 archivos**.
- Los sidecars están atados al festival (`<fid>-*.json`) y se indexan por título verbatim del festival: la misma decisión («Somnolítico», «Sol de niebla», «Quazar», «The Travelers», «Tuktu padre maíz», «El mundo de Humberto», «No es el fin del mundo») aparece declarada en más de un sidecar porque cada festival la re-declara. Total de títulos de sidecar que viven en ≥2 festivales: 10 (correcciones) + 4 (sinopsis) + 44 (afiches) = 58 decisiones repetibles.

## 7. Cómo se reusa hoy lo ya publicado (pipeline/lib.py + pipeline/enriquecer.py)

1. `lib.obras_publicadas(repo, excluir)` indexa TODOS los `festivals/*.json` (archivados incluidos, cortos de `film_list` incluidos, sin `type=="event"`) por `norm(title)` → `[(festival, obra)]`. Se construye en cada corrida del enriquecido, excluyendo el festival propio.
2. `lib.ya_publicada(obra, idx)` cruza por título (igual o uno es prefijo entero del otro) **y** algo que lo corrobore: director (`director_coincide`), o si un lado no trae director, duración ±3 o año ±1. Devuelve por cada coincidencia solo: `festival, titulo, tmdb_id, poster, posterSource, lbSlug, sinopsis`.
3. `enriquecer.cascada_tmdb` busca la ficha de TMDB en 3 pasos: (a) candado director + año/duración; (b) título idéntico + director; (c) el `tmdb_id` con que ya la publicamos en otro festival, pero solo si TMDB confirma la dirección (otra llamada a credits). Lo publicado es el TERCER camino, no el primero.
4. Si TMDB no trae sinopsis en español y algún festival nuestro ya la publicó con una, se reusa esa (`_sinopsis_de: ya publicada en X`).
5. `enriquecer.reuso_publicada(pub, fid)` cubre la obra SIN ficha TMDB (o con ficha sin póster): reusa el póster de otro festival si existe en disco, no es `editorial`, no es del festival propio y pasa `afiche_criterio`; y la sinopsis de donde esté. Cascada del afiche: TMDB → publicado → declarado en `<fid>-afiches.json`.
6. Lo que SÍ viaja: tmdb_id (verificado de nuevo), poster (ruta `/assets/<otro-fest>/…` reutilizada, no copiada), sinopsis ES, lbSlug.
7. Lo que NO viaja: `synopsis_en`, `title_en`, `year`, `duration`, `country`/flags, `genre`, `language`, `director` normalizado (cada festival publica el suyo: de ahí los 27 directores y 24 años contradictorios del punto 3).
8. Tampoco viajan las DECISIONES: `<fid>-correcciones.json` (ficha declarada a mano / tmdb forzado), `<fid>-sinopsis.json` y `<fid>-afiches.json` se leen solo para su festival; una obra que vuelve en otro festival obliga a re-declarar (58 casos ya repetidos, punto 6). El afiche declarado sí llega indirectamente al siguiente festival vía el póster ya publicado (paso 5), pero no su fuente ni su porqué.
9. El reúso es por título+corroboración, no por identidad: «Soñé su nombre» (Ángela Carabalí) está como 2 obras distintas (tmdb 1454365 en ficma/jardin/narrarelfuturo; sin tmdb en ficdeh/qaff/siembrafest) y 127 títulos normalizados caen en más de una clave (con tmdb_id vs sin, o director escrito distinto) → la cifra de 2571 únicas es un TECHO; por solo título hay ~2.43k (ver cifra abajo).
10. No hay escritura de vuelta: el festival nuevo nunca mejora al viejo (si hoy conseguimos tmdb_id, sinopsis EN o afiche mejor, el festival anterior se queda como estaba). La única memoria compartida es la lectura del JSON publicado; no existe un catálogo canónico ni un id propio para las 1651 obras sin tmdb_id.

### Cifra de contraste (solo título normalizado, sin director ni tmdb_id)
- Obras únicas por solo título: **2442** (vs 2571 por tmdb_id/título+director) → entre 2.44k y 2.57k obras únicas reales.
- Títulos en ≥2 festivales por solo título: **195** (vs 125 con la clave estricta): la clave estricta separa ~70 repeticiones por director escrito distinto o por tmdb_id presente en un festival y ausente en otro.

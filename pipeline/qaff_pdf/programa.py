# -*- coding: utf-8 -*-
"""La programación de Bogotá TRANSCRITA del PDF oficial, página por página.

Por qué transcrita y no parseada: las páginas de Cinemateca son tablas a dos
columnas —primero los horarios, después las obras en el mismo orden— y el texto
del PDF las entrega aplanadas. Un parser que las lea por posición acierta hasta
que un bloque tiene una sinopsis en medio, y entonces corre las obras un turno
sin avisar. Lo que da confianza aquí no es el parser: es que CADA título,
duración y hora de esta tabla se verifica contra el texto de la página que dice
ser su fuente (verifica.py). Si el festival reimprime, la verificación falla.

Página de origen entre paréntesis. Fechas: 2026.
"""

AF  = 'Alianza Francesa'
PUJ = 'Pontificia Universidad Javeriana'
UA  = 'Universidad de los Andes'
CIN = 'Cinemateca de Bogotá'
MN  = 'Museo Nacional de Colombia'
UN  = 'Universidad Nacional de Colombia'

# ── proyecciones ────────────────────────────────────────────────────────────
# (sede, sala, día, hora, [obras], página)
FUNCIONES = [
 (AF, None, '14', '15:00', ['FACE TO FACE','MANGO','CONCRETE MOVES'], 14),
 (AF, None, '15', '15:00', ['CAFE ?','Happy Meal','GLORIA','THE ONE WHO CRIES'], 14),
 (AF, None, '16', '15:00', ['CAPTAIN ANTHONY','LEER EN LAS GOTAS DE LLUVIA',
                            'A KING DISPLACED',
                            'SISTERS IN DESTINY: ANGELA DAVIS & GERTY ARCHIMEDE'], 19),
 (AF, None, '17', '15:00', ['PERFORMANCE ARTISTICA E MUSICAL','NI CHAÎNES NI MAÎTRES'], 19),

 (PUJ, 'Auditorio Centro Ático', '15', '10:00',
  ['CAIDA LIBRE','KANEKALON','BERTHA','HACKER LEONILIA','VICHE','TIA CIATA'], 27),
 (PUJ, 'Estudio 4 - Edificio Gerardo Arango, S.J. – Facultad de Artes', '16', '10:00',
  ['LA TINAJA','THE LAST DANCE','WATERFRONT MEMORIES','WHEN THE WORLD BROKE OPEN'], 27),
 (PUJ, 'Sala 901 - Edificio Jorge Hoyos Vásquez, S.J.', '17', '10:00',
  ['REFUGIAR EL GESTO','POSESAS','ALTANEGRA','SOÑÉ SU NOMBRE'], 37),
 (PUJ, 'Sala 903 - Edificio Jorge Hoyos Vásquez, S.J.', '18', '10:00',
  ['AMAZONAS COCINAS INDIGENAS DE SELVA Y RIO','MOJUGBA','A COR DA PATROA',
   'RELATOS DE LA GUAJIRITA'], 37),

 (UA, None, '15', '14:00', ['FITOFASCIAS','AISHA NO PUEDE VOLAR LEJOS'], 45),
 (UA, None, '16', '13:00', ['CAIDA LIBRE','REFUGIAR EL GESTO','KANEKALON','BERTHA',
                            'HACKER LEONILIA','TIA CIATA'], 45),
 (UA, None, '17', '14:00', ['THE BLACK BART OF TACO KING #17','STORMY DAYS','AMELIA',
                            'MI VICHE TODO EL DIA'], 51),
 (UA, None, '18', '13:00', ['ORANGO'], 51),

 (CIN, 'Sala 3', '15', '14:00', ['LOS CHICOS DEL BANJO'], 70),
 (CIN, 'Sala 3', '15', '17:00', ['HYPHEN'], 70),
 (CIN, 'Sala 3', '15', '19:30', ['EL ANCLAJE DEL TIEMPO'], 70),
 (CIN, 'Sala 3', '16', '14:00', ['SOBREVIVIENDO A BIAFRA'], 73),
 (CIN, 'Sala 3', '16', '17:00', ['TRES HOMBRES NEGROS'], 73),
 (CIN, 'Sala 3', '16', '19:30', ['NUNKUI'], 73),
 (CIN, 'Sala 3', '17', '14:00', ['DE BARRO Y SANGRE'], 76),
 (CIN, 'Sala 2', '17', '15:00', ['VIVA YURUMANGUI'], 76),
 (CIN, 'Sala Capital', '17', '16:30', ['LA OBRA DE DIOS'], 76),
 (CIN, 'Sala 3', '18', '14:00', ['LOS VIAJEROS'], 79),
 (CIN, 'Sala 3', '18', '17:00', ['INICIACIÓN EN LA OCTAVA DIMENSIÓN'], 79),
 (CIN, 'Sala 3', '18', '19:30', ['GENERACIÓN EQUIVOCADA'], 79),
 (CIN, 'Sala 3', '19', '14:00', ['CAIDA LIBRE','BERTHA','AVENIDA FISHKILL 305',
                                 'UN DOMINGO','AMELIA','CAFE ?'], 82),
 (CIN, 'Sala 3', '19', '19:30', ['DÍA DEL PADRE'], 82),
 (CIN, 'Sala 3', '20', '14:00', ['AMAZONAS COCINAS INDÍGENAS','CARABALÍ',
                                 'UN REY DESPLAZADO',
                                 'HERMANAS EN EL DESTINO - ANGELA & GERTY ARCHIMÈDE'], 84),
 (CIN, 'Sala 3', '20', '17:30', ['EL COACH DE LOS LOCOS'], 84),
 (CIN, 'Sala Capital', '20', '18:30', ['AISHA NO PUEDE VOLAR LEJOS'], 84),
]

# Nombre y sinopsis que el propio festival le puso a dos bloques (p82, p84).
# Donde el festival NOMBRA un conjunto hay contenedor; donde no, la función es
# la obra (docs/SCHEMA.md, modelo A).
# El programa los imprime en VERSALES, como todo lo suyo. El guardián de la app
# rechaza títulos en ALLCAPS: la app escribe en Title Case, y unas versales
# sueltas gritan en la parrilla. Es la misma normalización que se le hace a
# los títulos de obra, no una reescritura del nombre.
BLOQUES = {
 (CIN,'19','14:00'): ('Bloque cortos ficción — Noir urbano: historias en clave menor',
   'Seis miradas breves que encuentran lo extraordinario en lo cotidiano, un domingo '
   'cualquiera, una taza de café, un encuentro casual y revelan las tensiones raciales, '
   'familiares y sociales que atraviesan la vida diaria en cuatro continentes.'),
 (CIN,'20','14:00'): ('Bloque cortos documental — Noir memorias: de la sombra al testimonio',
   'Cuatro documentales que rescatan saberes, historias y luchas silenciadas, para '
   'reafirmar que la memoria es, en sí misma, un acto de resistencia.'),
}

# ── actividades: los Diálogos Improbables y lo que no es proyección ─────────
# Cada uno tiene DOS páginas: la parrilla lo anuncia y una página propia da
# moderador, panelistas, fecha, hora y sede. La hora sale de la página propia.
ACTIVIDADES = [
 ('dialogo', AF,  None, '14', '15:00', '17:00', 'NOIR ESTÉTICO: La estética de la oscuridad',
  'Florent Mahoukou · Gwladys Gambie · Catalina Mosquera · Shamyr Caicedo Rivas · Santiago Trujillo', 15),
 ('dialogo', PUJ, 'Auditorio Centro Ático', '15', '10:00', '13:00',
  'NOIR MEMORIA: Matriarcado negro y territorio sonoro',
  'Modera María José López · Emma Van Lare · Ana Beatriz Silva · Mariana Campos · Wilson Borja', 32),
 ('dialogo', UA,  None, '15', '14:00', '16:00', 'NOIR IDENTIDAD: Territorios rotos, cuerpos que resisten',
  'Moderan Melissa Riquet, Sofía Espinosa y María José Durán · Juan Manuel Amaya · Douna Tongrongru · Petra Ventana · Maguemati Wabgou', 47),
 ('dialogo', PUJ, 'Estudio 4 - Edificio Gerardo Arango, S.J. – Facultad de Artes', '16', '10:00', '13:00',
  'NOIR INDUSTRIA: Redes Sur-Sur. Circulación y mercados Sur-Sur',
  'Modera Marcio Brito Neto · Andrea V. Naranjo · Yenni Córdoba · Marino Aguado · Marton Olympio', 36),
 ('dialogo', MN,  'Auditorio Teresa Cuervo Borda', '16', '10:00', '12:00',
  'NOIR IDENTIDAD: Ser negro no es un género',
  'Modera Indhira Serrano · César Palacios Chaverra · Patricia Mena · Nicolás Vizcaíno Sánchez · Alejandra Mina', 58),
 ('dialogo', PUJ, 'Sala 901 - Edificio Jorge Hoyos Vásquez, S.J.', '17', '10:00', '13:00',
  'NOIR: Después de la tormenta — cuerpo, tierra y renacer',
  'Modera Frida Muenala · Julián Díaz · Juliana Carabalí · Nina Caicedo · Yenni Córdoba', 38),
 ('dialogo', AF,  None, '17', '15:00', '18:00', 'NOIR INDUSTRIA: Circulación y mercados Sur-Sur',
  'Modera Ángel Perea Escobar · Essehomo Pino Valoyes · Alain Nkosi Nkonda · Zanu · Lucas Silva', 22),
 ('dialogo', MN,  'Auditorio Teresa Cuervo Borda', '17', '16:00', '18:00',
  'NOIR HISTÓRICO: Las sombras del archivo',
  'Modera Catherine Dunga · Gwladys Gambie · Ángela Carabalí · Carlos Correa Angulo · Mercedes Angola', 62),
 ('dialogo', PUJ, 'Sala 903 - Edificio Jorge Hoyos Vásquez, S.J.', '18', '10:00', '13:00',
  'NOIR FOGÓN: Cocina, territorio y memoria',
  'Modera Ana Camila Jaramillo · Miguel Ángel Abadía · Ricardo Malagón', 43),
 ('dialogo', UA,  None, '18', '13:00', '16:00', 'NOIR Y GÉNERO: Mujeres en el cine',
  'Moderan Melissa Riquet, Sofía Espinosa y María José Durán · Catalina Mosquera · Frida Muenala · Nina Caicedo', 54),
 ('dialogo', UN,  'Facultad de Artes', '22', '16:00', '18:00',
  'NOIR ESTÉTICO: La imagen entre el lienzo, el archivo y la pantalla',
  'Modera Iván Jiménez · Wilson Borja · Francisco Caldas Vela · Rafael Antonio Díaz', 67),
 # La página del vernissage (p24) NO imprime hora: solo «17 Septiembre 2026» y
 # «Entrada Libre». La franja sale de la parrilla que lo contiene (p19, 3:00-8:00
 # pm del 17). Ponerle una hora propia sería inventarla.
 ('vernissage', AF, None, '17', '15:00', '20:00', 'Vernissage — Ma chérie, coiffure?, de Phalonne Pierre Louis',
  'Exposición de Phalonne Pierre Louis. Entrada libre.', (19, 24)),
]

# La sede abre una hora y media antes de la primera función, los seis días de
# Cinemateca. No es una función: no se le puede poner en la agenda a nadie.
APERTURAS = [(CIN, d, '13:30') for d in ('15','16','17','18','19','20')]

SEDES_DIR = {
 AF:  'Cra. 3 # 18-45, Bogotá',
 PUJ: 'Cra. 7 # 40-62, Bogotá',
 UA:  'Cra. 1 # 18A-12, Bogotá',
 CIN: 'Cra. 3 # 19-10, Bogotá',
 MN:  'Cra. 7 # 28-66, Bogotá',
 UN:  'Cra. 45 # 26-85, Bogotá',
}
# El 16 en Javeriana NO es en el campus de la Cra. 7: es Calle 40B # 5-37.
SALA_DIR = {'Estudio 4 - Edificio Gerardo Arango, S.J. – Facultad de Artes':
            'Calle 40B # 5-37, Bogotá'}

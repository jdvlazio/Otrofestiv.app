// ══════════════════════════════════════════════════════════════════
// FUENTE ÚNICA DE VERDAD — Textos del UI
// Cambiar aquí aplica en toda la app automáticamente.
// ══════════════════════════════════════════════════════════════════
const UI = {
  badge: {
    cancelled:    'CANCELADA',
    rescheduled:  'REPROGRAMADA',
    qa:           'Q&A',
    inscription:  'INSCRIPCIÓN',
    past:         'Pasó',
    soon:         'PRONTO',
  },
  travel: {
    walking: 'a pie',
    transit: 'en carro',
  },
  action: {
    add:      'Añadir',
    remove:   'Quitar',
    confirm:  'Confirmar',
    cancel:   'Cancelar',
    save:     'Guardar',
    close:    'Cerrar',
    restore:  'Restaurar',
    rate:     'Calificar',
    change:   'Cambiar',
    addPlan:  'Añadir a mi plan',
  },
  empty: {
    noActivity:  'Sin actividades para este día',
    noResults:   'Sin actividades para este filtro',
    noPending:   'No hay películas pendientes',
    planCovered: 'Añade más títulos en Intereses para ver sugerencias adicionales.',
    allPassed:   'Todas las actividades de tu plan ya pasaron',
    overlap:     'Hay actividades con horario solapado',
  },
};

let FILMS=[];
let POSTERS={};
let CUSTOM_POSTERS={};


const TMDB_IMG="https://image.tmdb.org/t/p/w185";
const FICCI_POSTER_URL='https://ficcifestival.com/sites/default/files/2026-02/logo-ficci65_2.png';

/* ── POSTER GENERATIVO — identidad Otrofestiv para programas ──────────
   REGLA CANÓNICA — nunca romper sin justificación explícita:

   PRIORIDAD DE POSTER (en todo contexto — grilla, card, Mi Plan):
     1. Poster real (CUSTOM_POSTERS > SHORT_IMGS > POSTERS/TMDB)
     2. Poster generativo (solo si no hay real)
     3. Placeholder vacío (surf-2) — nunca negro

   TIPOS DE POSTER GENERATIVO — mismo _buildPosterSVG, misma plantilla:
     · Competencia cortos → header teal  · l1:'COMPETENCIA' · l2:'CORTOMETRAJES'
     · Programa cortos   → header teal  · l1:'PROGRAMA'    · l2:'CORTOMETRAJES'
     · Evento/Industry   → header ámbar · l1:'INDUSTRY'    · l2:'DAYS'

   REGLA DE DETECCIÓN:
     f.type === 'event'  → makeEventPoster()
     f.is_cortos === true → getPosterSrc(title,true) || makeProgramPoster(title,dur,section)
     resto               → getPosterSrc(title,false) || null

   ONERROR: siempre this.remove() — nunca this.style.opacity=0
   TÍTULO: limpiar prefijos redundantes en makeProgramPoster()
────────────────────────────────────────────────────────────────────── */
const SHORT_IMGS={"Ghost Strata": "https://image.tmdb.org/t/p/w92/a03LyOUDzsslvweETxrLF7g13Z1.jpg", "Slow Action": "https://image.tmdb.org/t/p/w92/mtmL6Jg517QyPBl7nOC0hEI7dSE.jpg", "This Is My Land": "https://image.tmdb.org/t/p/w92/cZZDiPzFc0V628Of5GMgvQVyBVM.jpg", "Ah, Liberty!": "https://image.tmdb.org/t/p/w92/yI5spv1sccMarSNzKXuC0woXkeI.jpg", "Two Years at Sea": "https://image.tmdb.org/t/p/w92/eBy5Y543lS3jhvcDNp4uBNDxLpI.jpg", "A Running Woman (1, 2, 3)": "https://image.tmdb.org/t/p/w92/2YHPPGfd7GQlTE5r3c4Hlijsorv.jpg", "Instant Life": "https://image.tmdb.org/t/p/w92/tjzeeyKk9nY2Ek8W1KK5NyZopMU.jpg", "Come and Dance with Me": "https://image.tmdb.org/t/p/w92/lCAGVjfOqLluZVCfJ5Rqi74OyXi.jpg", "Gente perra": "https://image.tmdb.org/t/p/w92/tRZcXstcIDLw1K8On51WXL8y1oG.jpg", "A Flea's Skin Would Be Too Big for You": "https://image.tmdb.org/t/p/w92/dVBwHO487uMYnzBcAwtKmy8WEfI.jpg", "Fuego en el mar": "https://image.tmdb.org/t/p/w92/sWItTOPiellWkuG8H1Gb70LWI9p.jpg", "Ali au pays des merveilles": "https://image.tmdb.org/t/p/w92/z7djyMjFNZSxYaImAQ5DJHtorgL.jpg", "Cul-De-Sac!": "https://image.tmdb.org/t/p/w92/lpcPZ6dfJFLjpeDAuvsMi11amOR.jpg", "Ein Unfall": "https://image.tmdb.org/t/p/w92/mMwxovImXvfegUlzJWo37OuYcaN.jpg", "Force Times Displacement": "https://image.tmdb.org/t/p/w92/1Ix7UsaMvxiL3yFVxngYAdvCrPy.jpg", "Luna Rossa": "https://image.tmdb.org/t/p/w92/cOjnO0TenOYL2HMNmaxlGdA4NhV.jpg", "Evacuations": "https://image.tmdb.org/t/p/w92/mzDgA3o8Xx9m4A1AEOmz8DrNrnc.jpg", "El cuento de Antonia": "https://image.tmdb.org/t/p/w92/sK1dtEiHts0gnyPccusSiJtsWdV.jpg", "Flores del otro patio": "https://image.tmdb.org/t/p/w92/icXmSR2VtpFsfeP0BHHvVwehP8g.jpg", "Como Nasce um Rio": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Poster_EN_How%20A%20River%20Is%20Born%20%281%29%20-%20Clara%20Fl%C3%B4res.png?itok=7vkG9BHm", "Taxi Moto": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_affiche_MOTOTAXI_GB_1500x2000%20-%20Festivals%20Sudu.jpg?itok=7LEPmRue", "Voz, Zov, Zvo": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/CARTAZ%20ZOV%20-%20P%C3%AA%20Moreira%20-%20Por%20Extenso%20Produ%C3%A7%C3%B5es_0.jpg?itok=8BtA2E2m", "Runa Simi": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/RUNA%20SIMI%20POSTER%20AF%20-%20Claudia%20chavez%20levano.jpg?itok=ObXBIPVJ", "Tu mañana será mi canto": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_TuMan%CC%83anaSera%CC%81MiCanto_Poster%20-%20Fernando%20Saldivia%20Y%C3%A1%C3%B1ez.jpg?itok=O0EAsSCB", "Ángeles somos": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_angeles%20somos%20poster%20-%20KIZZIS%20RADE.png?itok=9K9uH-kw", "Héroes del silencio": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_4_He%CC%81roes%20del%20Silencio_Po%CC%81ster%20-%20Santiago%20Alejandro%20Mu%C3%B1oz%20Marrugo.jpg?itok=NGH1UWzS", "El reportaje": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Poster%20El%20Reportaje%20-%20Henry%20Laserna.jpeg?itok=ZqJjHget", "Kuagro": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/poster%20KUAGRO%20FINAL_Mesa%20de%20trabajo%201%20-%20Diego%20Casseres.png?itok=qvukayHP","Futuros luminosos": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_P%C3%B3ster%20Futuros%20luminosos%20-%20Ismael%20Garcia.jpg?itok=6WCvT13b", "La forma y la raíz": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_poster%20la%20forma%20y%20la%20raiz%20-%20Nathalia%20Quimbay%20Cadena.jpg?itok=dR-4fsTr", "Sombras en la niebla": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_afiche%20SELN%20-%20Pedro%20Vega_0.jpg?itok=2FqonkaA", "Winter Blumen Garten": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_WINTER_BLUMEN_GARTEN_POSTER_ESP_1%20-%20EXPERIMENTA.jpg?itok=dZG03ssO", "Todas las manos que solté": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-25%20155500.png?itok=liUEj-a0", "Montaña luminosa": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_ML%20Poster%20FICCI%2065%20-2026%20-%20Lony%20Welter.png?itok=0KYb7rep", "Las formas de la magia": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_LFM_poster_Ficci_595x842%20-%20Maria%20Paula%20Lorgia.jpg?itok=5XCaIr83", "Pawa": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Portada%20Pawa%20png%20-%20Aguacate%20Audiovisual.jpg?itok=qWnn1F5-", "La garganta del diablo": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_LaGargantadeDiablo%20-%20Juanita%20Urue%C3%B1a%20Barreto.png?itok=WsH78OYf", "Suite intercontinental": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Capture_decran_2025-05-28_a_15.57.26%20-%20Marianna%20Manili.jpg?itok=alqasZXz", "Belleza letal": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_afiche%20belleza%20letal%20-%20Samuel%20Moreno.jpg?itok=ZrOw0nvZ", "Consagración": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_FICCI_xPosters_Instagram_4x5_9x162%20-%20Vanessa%20Monti.png?itok=9P9UU2BT", "Madres de nacimiento": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_MDN_Poster_Blanco_WEB.jpg?itok=OR2_OCi0", "Lejanía": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_PO%CC%81STER%20LEJANIA%20-%20Carolina%20Zarate%20Garcia.png?itok=UPHrcFZ4", "El cazador": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-30%20170710.png?itok=dXa68A0J", "Decaer": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-04%20a%20la%28s%29%203.43.18%20p.m..jpg?itok=SfE8u2Hj", "Ya se ven los tigres en la lluvia": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-23%20202933.png?itok=fJ60ATsd", "Filme Pin": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_POSTER-FILME-PIN-2026%20-%20La%20Vulcanizadora.jpg?itok=qrKWWtjf", "Sirena mecánica": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-23%20205043.png?itok=BR7oyf-o", "Mi amigo, el arquitecto": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_MFTA_Final_Untextured_Low-Res%20-%20MEDIOCIELO%20Cine%20%281%29.jpg?itok=MXASl-yt", "Samba Infinito": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/SAMBA-INFINITO-POSTER-VERSION-02_LOW%20-%20Leonardo%20Martinelli.jpg?itok=amDXZSrX", "Agua fría": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-01%20a%20la%28s%29%207.42.27%20p.m..jpg?itok=Ygi-1TlW", "Fim de Rodovia": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/FimdeRodovia_Poster%20-%20Valentina%20Rosset.jpeg?itok=T6gk5I3T", "Los peces no se ahogan": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Poster%20LPNSA%20-%20Le%CC%81a%20Vidotto%20%281%29.png?itok=p1sNnCoH", "Quem se Move": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_QSM-cartaz-3-PT-menor%20%281%29.png?itok=PlEjYkVF", "Pajuyuk": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_POSTER_PAJUYUK-LAURELES%20-%20A%20POSTERIORI%20ENTERTAINMENT.jpg?itok=PWKdk9HE", "A donde nos lleva la fe de José Gerónimo": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Poster_adondenosllevalafedeJoseGeronimo_011.jpg?itok=X2Ld7Y2V", "O Mapa em que Estão os Meus Pés": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_CARTAZ_CORRECAO%20-%20luciano%20pedro.jpg?itok=Y7jI8K3m", "En otra Palestina": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_EOP_Poster_FICCI.jpg?itok=HNZnf8_-", "Fuente alemana": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_fuente%20alemana2%20-%20Galleryr3.jpeg?itok=VmP1Zq8n", "Abortion Party": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Abortion%20Party%20-%20Poster.png?itok=Vh79cJxK", "Trizas": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Afiche%20C-ESP%20%28A2%20RGB%20300dpi%29%20-%20Pau%20Pascua.jpg?itok=kL9mQ1Xp","Atado": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_ATADO_POSTER%20%281%29%20-%20Ran%20Shao.jpg?itok=3ykhh5PE", "Pequeno Jogo": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_PEQUENO-JOGO-POSTER_ES%20-%20Sofia%20Tomic.png?itok=ZkyptTrE", "Trưa Lịm": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-23%20211541.png?itok=GbDa6pdw", "Warnungen an die ferne Zukunft": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Warnungen%20an%20die%20ferne%20Zukunft%20PLAKAT%20-%20Ju%20liane_page-0001.jpg?itok=BKoBLV6t", "3cm of Complexity": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Film%20Poster_3cm%20of%20Complexity%20-%20Fanny%20Berghofer.jpg?itok=RsFqy5mK", "Mapalé": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Mapale%20-%20Yan%20Dec%20%281%29_0.png?itok=GhrVrm0p", "Soeurs Jarariju": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Screenshot%202026-04-04%20at%2023.27.1.png?itok=rlQuj2tc", "Les Trois Hirondelles": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Les_trois_hirondelles2%20-%20Yan%20Dec.jpg?itok=HNjh4Nx6", "Sonali": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/254919-1920x1054%20-%20Yan%20Dec.jpg?itok=EeAwmLhP", "Ako počúvať fontány": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Screenshot%202026-04-05%20at%2000.25.0.png?itok=UO8Zgy0V", "La baraja de Myriam": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Screenshot%202026-04-05%20at%2000.29.4.png?itok=cUJ_Btno", "Venezia Diorama": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Screenshot%202026-04-05%20at%2000.35.2.png?itok=QQDpFBWe", "La Raya": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Captura%20de%20pantalla%202026-03-29%20235923.png?itok=0Rlq5ukp", "Apotnojushi La casa del viento": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_PORTADAS%20CASA%20EN%20EL%20%20aire%202-im%C3%A1genes-0%20-%20Aguacate%20Audiovisual.jpg?itok=b37CurBg", "La tinaja": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_POSTER_SIN%20CREDITOS%20copia%20-%20Mar%20Aj%C3%A9.jpg?itok=Dhen7YE6", "Piratas de La Boquilla": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Portada%20piratas%20de%20la%20boquilla.jpg%20-%20Cra%2073%20Club.jpeg?itok=WV1ROqrJ", "A donde nos lleva la fe de José Gerónimo": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/result_Poster_adondenosllevalafedeJoseGeronimo_011.jpg?itok=aCpXNMkE","An Incomplete Calendar": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-01%20a%20la%28s%29%2016.28.13.png?itok=znYWjLkI", "No les pedimos un viaje a la luna": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/sf-poster-nolespedimos.jpg?itok=H8njrtBo", "Ali au pays des merveilles": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/images-original%20%281%29.jpg?itok=ldu9nBqc", "Nicaragua, semilla de soles": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-01%20a%20la%28s%29%2017.58.43.png?itok=YZyn6Dtw", "Petrolita": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-03-02%20a%20la%28s%29%2011.35.28%20-%20Adria%CC%81n%20Iturralde.png?itok=_QYZJ_UL", "Fuego en el mar": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Afiche%20Fuego%20en%20el%20mar%20%281%29.jpg?itok=scGRKes4", "Viaje a la explotación": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/ViajeExplotacion%20-%20Josep%20Calle.jpg?itok=pU71m7-F", "¡Aysa!": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-01%20a%20la%28s%29%2017.12.48.png?itok=hz4I9Ged", "Comunicado de Argentina": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/comunicado1-992x744%20-%20Carolina%20Cappa.jpg?itok=4ILAHwdM", "Palestina, otro Vietnam": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Portada%20-%20POV.jpg?itok=KiL9H_9L", "Riochiquito": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-01%20a%20la%28s%29%2021.59.57.png?itok=1-wp2Q2u", "A World Rattled of Habit": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/a%2Bworld%2Brattled%2B1.jpeg?itok=-_KI4p80", "Origin of the Species": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/origin%20s%20thru%20trees.jpeg?itok=oEJXHvsj", "Ah, Liberty!": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Ah%252C%2BLiberty%2521%2B3%2Bcopy.jpg?itok=ZTE4aLZH", "This Is My Land": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/this%20is%20my%20land%202.jpg?itok=o8AguBHA", "Urth": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Urth%2B3.jpg?itok=8EYylnMd", "Look Then Below": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Look%20Then%20Below%208.jpeg?itok=GvGZteEc", "Slow Action": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/SLOW%2BACTION%2BHD%2B17.jpeg?itok=EeNxF7Dz", "Things": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Things%2B9%2Ba%252C%2Bb%2Bbook.jpg?itok=dA3ARMJ6", "The Shape of Things": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/stateofthings%2B1.jpeg?itok=DIUYu98C", "Ghost Strata": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Ghost%2BStrata%2Bstill%2B4_0.jpg?itok=DSphQJHs", "A Running Woman (1, 2, 3)": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20152313.png?itok=Z-p9Vizo", "Instant Life": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20154413_0.png?itok=y69N_vUg", "The Masked Monkeys": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20165739.png?itok=lr5goUXn", "Wolkenschatten": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20170542.png?itok=zXreDt0y", "Gente perra": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20171632_0.png?itok=sogZK08j", "A Flea's Skin Would Be Too Big for You": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20172446.png?itok=JLdRnxKz", "Come and Dance with Me": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20173312.png?itok=YL7Tv6gw", "Eigenheim": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Captura%20de%20pantalla%202026-04-05%20173912.png?itok=g_7kENPD", "Intersecting Memory": "https://ficcifestival.com/sites/default/files/styles/1920px_x_480px/public/img-catalogo/result_Intersecting%20memory%20photo%204%20-%20Association%20Grec.jpg?itok=1WX0MrRb", "Daria's Night Flowers": "https://image.tmdb.org/t/p/w92/hNuuQciHXD7VqBPHgNVKSHh4yLB.jpg", "Two Years at Sea": "https://ficcifestival.com/sites/default/files/styles/250px_x_312px/public/img-catalogo/Poster%20-%20TWO%20YEARS%20AT%20SEA.jpg?itok=yluyy15n"};
/* ══════════════════════════════════════════════════════
   SISTEMA DE PÓSTERS — fuente unificada y normalizada
   ─────────────────────────────────────────────────────
   FUENTES (en orden de prioridad):
     1. CUSTOM_POSTERS  — URLs manuales (Maspalomas, AnyMart…)
     2. SHORT_IMGS      — cortos: URLs directas TMDB/FICCI
     3. POSTERS         — features: URLs completas (TMDB o CDN propio)

   NORMALIZACIÓN:
     normKey(s) → convierte apostrofes Unicode → ASCII (U+0027)
     Se aplica a AMBOS lados (claves y título buscado).
     Previene mismatch entre U+2019 (tipográfico) y U+0027 (ASCII).

   REGLA: NUNCA acceder SHORT_IMGS/POSTERS/CUSTOM_POSTERS directamente
   en templates — siempre usar getPosterSrc(title, isCortos).
══════════════════════════════════════════════════════ */
const normKey = s => s.replace(/[\u2018\u2019\u201A\u201B\u2032\u02BC]/g, "'");

// Pre-normalizar claves de los tres diccionarios al cargar
let _CUSTOM_N = {};
const _SHORT_N   = Object.fromEntries(Object.entries(SHORT_IMGS).map(([k,v])=>[normKey(k),v]));
let _POSTERS_N = Object.fromEntries(Object.entries(POSTERS).map(([k,v])=>[normKey(k),v]));

function getPosterSrc(title, isCortos, section){
  const t = normKey(title);
  if(_CUSTOM_N[t]) return _CUSTOM_N[t];
  if(isCortos && _SHORT_N[t]) return _SHORT_N[t];
  if(_POSTERS_N[t]) return _POSTERS_N[t].startsWith('http')?_POSTERS_N[t]:TMDB_IMG+_POSTERS_N[t];
  if(isCortos) return null;
  return null;
}

// ═══════════════════════════════════════════════════════════════
// FUENTE ÚNICA DE VERDAD — getFilmPoster(f)
// ───────────────────────────────────────────────────────────────
// Recibe el objeto film completo. Devuelve siempre el poster
// correcto según el tipo. Nunca tomar esta decisión en otro lugar.
//
// TIPOS Y REGLAS:
//   f.type === 'event'   → poster ámbar generativo
//   f.is_cortos === true → poster real si existe, teal generativo si no
//   corto individual     → getPosterSrc(title, true) — busca en SHORT_IMGS
//   película             → poster real si existe, null si no
//
// USO: getFilmPoster(f) en TODOS los contextos — grilla, card, lista, Mi Plan
// ═══════════════════════════════════════════════════════════════
function getFilmPoster(f){
  if(!f) return null;
  if(f.type==='event') return makeEventPoster(f.title,f.duration);
  // film.poster — fuente directa, máxima prioridad (Fase 1.2)
  if(f.poster) return f.poster;
  if(f.is_cortos) return getPosterSrc(f.title,true)||makeProgramPoster(f.title,f.duration,f.section);
  if(f.is_programa&&f.film_list&&f.film_list.length){
    const first=f.film_list[0];
    return getPosterSrc(first.title||first,false)||getPosterSrc(f.title,false)||null;
  }
  return getPosterSrc(f.title,false)||null;
}

// Para cortos individuales dentro de un film_list (no tienen objeto film completo)
function getCortoItemPoster(item){
  if(!item) return null;
  return getPosterSrc(item.title,true)||null;
}

// ═══════════════════════════════════════════════════════════════
// 2 · SISTEMA DE ÍCONOS
//     LB_SVG (Letterboxd), ICONS (Lucide)
// ═══════════════════════════════════════════════════════════════
/* ── Letterboxd slugs — FUENTE ÚNICA: lista oficial FICCI 65 ───
   https://letterboxd.com/ficcifestival/list/ficci-65/detail/
   Extraídos directamente del DOM con Claude in Chrome.
   Sin inferencias. Sin suposiciones.
   Replicable: extraer desde la lista oficial del festival en LB.
──────────────────────────────────────────────────────────────── */
let LB_SLUGS={};
let LB_SLUGS_AFF={};
let FILMS_AFF=[];
let POSTERS_AFF={};
// ── Avisos de festival: funciones canceladas o reprogramadas ──────────────
// type: 'cancelled' | 'rescheduled'
// date: 'YYYY-MM-DD' de la función original — el banner desaparece al día siguiente
// Para 'rescheduled': añadir newDay, newTime, newVenue
const NOTICES=[
  {title:'La misteriosa mirada del flamenco',festival:'aff2026',type:'rescheduled',date:'2026-04-24',newDay:'VIE 24',newTime:'19:00',newVenue:'Cineprox Las Américas'},
  {title:'Rayas de tigre',festival:'aff2026',type:'rescheduled',date:'2026-04-25',newDay:'SÁB 25',newTime:'16:00',newVenue:'Cineprox Las Américas'},
  {title:'Un mundo frágil y maravilloso',festival:'aff2026',type:'rescheduled',date:'2026-04-26',newDay:'DOM 26',newTime:'13:30',newVenue:'Cineprox Las Américas'},
  {title:'Hacia casa',festival:'aff2026',type:'rescheduled',date:'2026-04-26',newDay:'DOM 26',newTime:'17:00',newVenue:'Cineprox Las Américas'},
];

const FESTIVAL_CONFIG={
  'ficci65':{
    name:'FICCI 65',shortName:'FICCI 65',city:'Cartagena',dates:'14\u201319 ABR',
    storageKey:'ficci65_',
    festivalEndStr:'2026-04-20T02:00:00',
    festivalDates:{'Martes':'2026-04-14','Miércoles':'2026-04-15','Jueves':'2026-04-16','Viernes':'2026-04-17','Sábado':'2026-04-18','Domingo':'2026-04-19'},
    days:[{k:'Martes',d:14,lbl:'MAR'},{k:'Miércoles',d:15,lbl:'MIÉ'},{k:'Jueves',d:16,lbl:'JUE'},{k:'Viernes',d:17,lbl:'VIE'},{k:'Sábado',d:18,lbl:'SÁB'},{k:'Domingo',d:19,lbl:'DOM'}],
    dayKeys:['Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'],
    dayShort:{'Martes':'MAR 14','Miércoles':'MIÉ 15','Jueves':'JUE 16','Viernes':'VIE 17','Sábado':'SÁB 18','Domingo':'DOM 19'},
    dayLong:{'Martes':'Martes 14','Miércoles':'Miércoles 15','Jueves':'Jueves 16','Viernes':'Viernes 17','Sábado':'Sábado 18','Domingo':'Domingo 19'},
    films:null,posters:null,lbSlugs:null
  },
  'aff2026':{
    name:'AFF 2026',shortName:'ALTERNATIVA',city:'Medellín',dates:'21\u201329 ABR',
    storageKey:'aff2026_',
    festivalEndStr:'2026-04-29T23:00:00',
    festivalDates:{'MAR 21':'2026-04-21','MIÉ 22':'2026-04-22','JUE 23':'2026-04-23','VIE 24':'2026-04-24','SÁB 25':'2026-04-25','DOM 26':'2026-04-26','LUN 27':'2026-04-27','MAR 28':'2026-04-28','MIÉ 29':'2026-04-29','JUE 30':'2026-04-30'},
    days:[{k:'MAR 21',d:21,lbl:'MAR'},{k:'MIÉ 22',d:22,lbl:'MIÉ'},{k:'JUE 23',d:23,lbl:'JUE'},{k:'VIE 24',d:24,lbl:'VIE'},{k:'SÁB 25',d:25,lbl:'SÁB'},{k:'DOM 26',d:26,lbl:'DOM'},{k:'LUN 27',d:27,lbl:'LUN'},{k:'MAR 28',d:28,lbl:'MAR'},{k:'MIÉ 29',d:29,lbl:'MIÉ'},{k:'JUE 30',d:30,lbl:'JUE'}],
    dayKeys:['MAR 21','MIÉ 22','JUE 23','VIE 24','SÁB 25','DOM 26','LUN 27','MAR 28','MIÉ 29','JUE 30'],
    dayShort:{'MAR 21':'MAR 21','MIÉ 22':'MIÉ 22','JUE 23':'JUE 23','VIE 24':'VIE 24','SÁB 25':'SÁB 25','DOM 26':'DOM 26','LUN 27':'LUN 27','MAR 28':'MAR 28','MIÉ 29':'MIÉ 29','JUE 30':'JUE 30'},
    dayLong:{'MAR 21':'Martes 21','MIÉ 22':'Miércoles 22','JUE 23':'Jueves 23','VIE 24':'Viernes 24','SÁB 25':'Sábado 25','DOM 26':'Domingo 26','LUN 27':'Lunes 27','MAR 28':'Martes 28','MIÉ 29':'Miércoles 29','JUE 30':'Jueves 30'},
    films:null,posters:null,
    lbSlugs:{
      'Homebound':'homebound-2025',
      'Un mundo frágil y maravilloso':'a-sad-and-beautiful-world'
    }
  }
};// Festival data loaded async from festivals/<id>.json via loadFestival()

let _activeFestId='ficci65';

// ═══════════════════════════════════════════════════════════════
// SUPABASE — Auth + Cloud Sync
// ═══════════════════════════════════════════════════════════════
const ICONS={
  star:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  starFill: `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  heart:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
  heartFill:`<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
  x:        `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  check:    `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block;flex-shrink:0"><polyline points="20 6 9 17 4 12"/></svg>`,
  undo:     `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;flex-shrink:0"><path d="M2.5 9C3.5 5.5 6.8 3 12 3a9 9 0 1 1-9 9"/><polyline points="2 3 2 9 8 9"/></svg>`,
  switch:   `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
  plus:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
  clock:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  play:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  calendar: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  alert:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  chevronR: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  chevronD: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  share:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>`,
  image:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
  search:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  pin:      `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
};

// Festival date map

// ═══════════════════════════════════════════════════════════════
// 3 · CONFIGURACIÓN
//     FESTIVAL_DATES, VENUES, PRIO_LIMIT, constantes Mi Plan
// ═══════════════════════════════════════════════════════════════
let FESTIVAL_DATES={
  'Martes':'2026-04-14','Miércoles':'2026-04-15','Jueves':'2026-04-16',
  'Viernes':'2026-04-17','Sábado':'2026-04-18','Domingo':'2026-04-19'
};
// Fin del festival — última función del Domingo + margen
let FESTIVAL_END=new Date('2026-04-20T02:00:00');
function festivalEnded(){ return simNow()>FESTIVAL_END; }

// Check if a screening has passed (with 10 min grace)

// ═══════════════════════════════════════════════════════════════
// 4 · UTILIDADES
//     Funciones puras: fechas, tiempo, conflictos, normalización
// ═══════════════════════════════════════════════════════════════

/* ── Venues — resolución de sedes para cualquier festival ─────────────
   _FEST_VENUES se carga desde el JSON del festival en loadFestival().
   VENUES es el fallback estático para FICCI 65.                      */
let _FEST_VENUES = {};
let _FEST_TRANSPORT = 'transit'; // 'walking' | 'transit' | 'mixed'

const VENUES={
  'Teatro Adolfo Mejía': {short:'Teatro Adolfo Mejía', lat:10.4238, lon:-75.5503},
  'Plaza Bocagrande':    {short:'Plaza Bocagrande',    lat:10.3987, lon:-75.5600},
  'CC Caribe Plaza':     {short:'CC Caribe Plaza',     lat:10.4071, lon:-75.5124},
  'Auditorio Nido':      {short:'Auditorio Nido',      lat:10.4250, lon:-75.5490},
  'Plaza Proclamación':  {short:'Plaza Proclamación',  lat:10.4230, lon:-75.5510},
  'C. Convenciones':     {short:'C. de Convenciones',  lat:10.4242, lon:-75.5497},
  'Unibac':              {short:'Unibac',               lat:10.4180, lon:-75.5430},
  'AECID':               {short:'AECID',                lat:10.4210, lon:-75.5470},
};
function _resolveVenue(v){
  if(!v) return null;
  if(_FEST_VENUES[v]) return _FEST_VENUES[v];
  const fk=Object.keys(_FEST_VENUES).find(k=>v.includes(k)||k.includes(v));
  if(fk) return _FEST_VENUES[fk];
  const sk=Object.keys(VENUES).find(k=>v.includes(k)||k.includes(v));
  if(sk) return VENUES[sk];
  return null;
}
const _TRAVEL_SCALE={
  walking:[{d:0.10,t:0},{d:0.35,t:5},{d:0.8,t:10},{d:1.5,t:20},{d:3.0,t:35},{d:Infinity,t:50}],
  transit:[{d:0.15,t:0},{d:0.40,t:8},{d:1.0,t:12},{d:2.5,t:18},{d:5.0,t:25},{d:Infinity,t:35}],
  mixed:  [{d:0.10,t:0},{d:0.35,t:5},{d:0.8,t:10},{d:1.0,t:12},{d:2.5,t:18},{d:5.0,t:25},{d:Infinity,t:35}],
};
function venueTravelMins(v1,v2){
  const c1=_resolveVenue(v1),c2=_resolveVenue(v2);
  if(!c1?.lat||!c2?.lat) return 0;
  const dlat=(c1.lat-c2.lat)*111;
  const dlon=(c1.lon-c2.lon)*111*Math.cos(c1.lat*Math.PI/180);
  const km=Math.sqrt(dlat*dlat+dlon*dlon);
  const scale=_TRAVEL_SCALE[_FEST_TRANSPORT]||_TRAVEL_SCALE.transit;
  const tier=scale.find(s=>km<=s.d);
  return tier?tier.t:35;
}
function vcfg(v){
  if(!v) return{short:''};
  const r=_resolveVenue(v);
  if(r) return r;
  return{short:v.split(' · ')[0].trim()};
}
function sala(v){const m=v.match(/Sala\s*(\d+)/)||v.match(/Sal[oó]n\s*(\d+)/i);return m?'Sala '+m[1]:'';}

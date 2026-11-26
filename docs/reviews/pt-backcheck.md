# Back translation check: Portuguese

Machine back translation into English, lowest word overlap first. A pointer for fluent reviewers, never a verdict: only a fluent speaker may set reviewed to true.

112 strings; 10 on the safety rail.

| Overlap | Safety | Key | ACE English | Locale text | Back translation |
|--:|:--:|:--|:--|:--|:--|
| 0% | yes | `safety.CALL_WORD` | Call {numbers} | Ligue {numbers} | Dial {numbers} |
| 0% |  | `scam.HEADLINES.LIKELY_SCAM` | LIKELY SCAM. | PROVÁVEL FRAUDE. | Probable fraud. |
| 0% |  | `scam.HEADLINES.SUSPICIOUS` | BE CAREFUL. | TENHA CUIDADO. | TAKE CARE. |
| 0% |  | `services.base.AREA_DEFAULT` | area | zona | zone |
| 0% |  | `services.base.DAYS` | Tue | ter | to have |
| 0% |  | `services.base.MONTHS` | Mar | mar | sea |
| 0% |  | `services.base.MONTHS` | Jun | jun | June |
| 0% |  | `services.base.MONTHS` | Jul | jul | July |
| 0% |  | `services.base.MONTHS` | Aug | ago | ago |
| 0% |  | `services.base.MONTHS` | Sep | set | set |
| 0% |  | `services.base.MONTHS` | Oct | out | out |
| 0% |  | `services.base.MONTHS` | Dec | dez | ten |
| 0% |  | `services.pregnancy.CALL` | Call {numbers}. | Ligue {numbers}. | Dial {numbers}. |
| 17% |  | `services.prices.CHANGE.same` | the same as {prev} | igual a {prev} | equal to {prev} |
| 19% |  | `scam.SIGNAL.refund_request` | it asks you to send back money sent by mistake | pede que devolva dinheiro enviado por engano | asks for a refund of money sent in error. |
| 28% |  | `services.warnings.STALE` | ACE could not check the {authority} warning feed recently, so it cannot tell if a warning is in force. Listen to official bulletins from {authority}. | O ACE não conseguiu consultar há pouco os avisos oficiais (fonte: {authority}) e não sabe se há algum em vigor. Ouça os boletins oficiais na rádio. | ACE was unable to consult the official notices a short while ago (source: {authority}) and does not know if any are in effect. Listen to the official bulletins on the radio. |
| 29% |  | `services.prices.CHANGE.down` | down {pct}% on {prev} | menos {pct}% que em {prev} | less {pct}% than in {prev} |
| 29% |  | `services.prices.CHANGE.up` | up {pct}% on {prev} | mais {pct}% que em {prev} | more {pct}% than in {prev} |
| 33% |  | `services.pests.NAMES.banana_xanthomonas_wilt` | banana Xanthomonas wilt | a murcha bacteriana da bananeira | bacterial wilt of banana plants |
| 33% |  | `services.prices.FOOT` | WFP prices. | Preços do PAM. | PAM prices. |
| 33% |  | `services.prices.UNIT` | per {unit} | por {unit} | by {unit} |
| 33% |  | `services.prices.UNIT_MANY` | per {unit} | por {unit} | by {unit} |
| 33% |  | `services.rain.FOOT` | Chances from the ECMWF forecast of {date}. | Probabilidades da previsão ECMWF de {date}. | ECMWF forecast probabilities for {date}. |
| 33% |  | `services.rain.WORDS.dry` | mostly dry | quase seco | almost dry |
| 33% |  | `services.warnings.NONE` | No official warning from {authority} covers {place} right now (checked {checked}). | Nenhum aviso oficial cobre {place} neste momento (fonte: {authority}, verificado a {checked}). | No official advisory covers {place} at this time (source: {authority}, verified at {checked}). |
| 36% |  | `services.prices.NO_FOOD` | ACE has no recent WFP price for {food} near {place}. | O ACE não tem preço recente do PAM para {food} perto de {place}. | ACE does not have recent PAM pricing for {food} near {place}. |
| 38% |  | `commands.TEXTS.language` | Reply LANG and a code: | Responda LINGUA e um código: | Answer with LANGUAGE and a code: |
| 38% |  | `services.facility.GAP` | ACE has no facility list for this country yet. | O ACE ainda não tem lista de unidades de saúde para este país. | ACE does not yet have a list of health units for this country. |
| 38% |  | `services.pregnancy.LATE` | At {w} weeks you are past the last planned check at 40 weeks. See a health worker today. | Com {w} semanas já passou a última consulta prevista, às 40 semanas. Veja um profissional de saúde hoje. | With {w} weeks, the last scheduled appointment, at 40 weeks, has already passed. See a healthcare professional today. |
| 38% |  | `commands.TEXTS.scam_usage` | Send SCAM followed by the message you are unsure about, and ACE will check it. | Envie FRAUDE seguido da mensagem de que desconfia, e o ACE vai verificá-la. | Send "FRAUDE" followed by a message explaining your suspicions, and ACE will verify it. |
| 39% |  | `services.pests.UNKNOWN` | ACE can check maize, cassava, banana and tomato so far. For other crops, ask an extension officer. | Por agora o ACE verifica milho, mandioca, banana e tomate. Para outras culturas, pergunte a um extensionista. | For now, ACE checks corn, cassava, bananas, and tomatoes. For other crops, ask an extension agent. |
| 40% |  | `scam.SIGNAL.unofficial_operator_number` | it claims to be Safaricom but gives a number other than 0722000000 | diz ser do operador mas dá um número que não é o oficial | It claims to be from the operator but gives a number that is not the official one. |
| 40% |  | `services.pests.NAMES.maize_lethal_necrosis` | maize lethal necrosis | a necrose letal do milho | lethal necrosis of corn |
| 40% |  | `services.rain.NEXT` | Plan field work for the drier days. | Planeie o trabalho no campo para os dias mais secos. | Plan your fieldwork for the driest days. |
| 41% |  | `services.pregnancy.DUE_NOW` | At {w} weeks, an antenatal check is due now. The next is at {next} weeks. | Com {w} semanas, tem uma consulta pré-natal agora. A seguinte é às {next} semanas. | At {w} weeks, you have a prenatal appointment now. The next one is at {next} weeks. |
| 42% |  | `scam.SIGNAL.prize_or_offer` | it says you have won something or offers money | diz que ganhou um prémio ou oferece dinheiro | says he won a prize or offers money. |
| 42% |  | `commands.TEXTS.tip_thanks` | Thank you. Your tip is saved for review by an expert. It will not be shared until it is checked. | Obrigado. A sua dica foi guardada para revisão por um especialista. Só será partilhada depois de verificada. | Thank you. Your suggestion has been saved for review by a specialist. It will only be shared after verification. |
| 42% |  | `services.prices.GAP` | WFP publishes no market prices for {country}, so ACE cannot give prices there. Ask traders or your agriculture office. | O PAM não publica preços de mercado para {country}, por isso o ACE não pode dar preços aí. Pergunte aos comerciantes ou aos serviços de agricultura. | The WFP does not publish market prices for {country}, therefore the ACE cannot provide prices there. Ask the traders or agricultural services. |
| 43% |  | `services.pests.NAMES.tomato_leaf_miner` | tomato leaf miner (Tuta absoluta) | a traça do tomateiro (Tuta absoluta) | the tomato leafminer (Tuta absoluta) |
| 44% |  | `services.base.NEEDS_PLACE` | Which {area} are you in? Reply with its name, for example {example}. | Em que {area} está? Responda com o nome, por exemplo {example}. | In which {area} is it located? Answer with the name, for example {example}. |
| 44% |  | `commands.TEXTS.clarify` | ACE has no checked guidance for that yet. ACE can help with: {topics}. Send TIP to suggest knowledge. | O ACE ainda não tem orientação verificada sobre isso. O ACE pode ajudar com: {topics}. Envie DICA para sugerir conhecimento. | ACE does not yet have verified guidance on this. ACE can help with: {topics}. Submit a TIP to suggest knowledge. |
| 46% |  | `services.prices.OLD` | The latest WFP price ACE holds for {country} is from {month}, too old to use. Ask traders or your agriculture office. | O último preço do PAM que o ACE tem para {country} é de {month}, antigo demais. Pergunte aos comerciantes ou aos serviços de agricultura. | The last PAM price that ACE has for {country} is from {month}, which is too old. Ask the traders or agricultural services. |
| 50% |  | `scam.SIGNAL.pressure` | it pressures you to act fast | pressiona-o a agir depressa | It pressures him to act quickly. |
| 50% |  | `services.pests.LIKELY` | This may be {problem}. ACE cannot see your crop, so check these signs: | Pode ser {problem}. O ACE não vê a sua cultura, por isso confirme estes sinais: | This could be a problem. The ACE doesn't see your culture, so check for these signs: |
| 50% |  | `services.prices.TOP` | Latest WFP prices at {market}{far}: | Últimos preços do PAM em {market}{far}: | Latest PAM prices on {market}{far}: |
| 50% |  | `services.warnings.FOUND` | Official warning for {place} from {authority}, until {until}: | Aviso oficial para {place}, até {until} (fonte: {authority}): | Official notice for {place}, until {until} (source: {authority}): |
| 50% |  | `services.warnings.MORE` | {n} more in force. | Mais {n} em vigor. | More {n} in effect. |
| 50% |  | `services.warnings.NATIONAL` | Official warning for the whole country from {authority}, until {until}: | Aviso oficial para todo o país, até {until} (fonte: {authority}): | Official notice for the entire country, until {until} (source: {authority}): |
| 51% |  | `commands.TEXTS.help` | ACE gives checked local guidance. Ask a question in your language. Commands: SCAM + message to check a message, TIP + your advice to share knowledge, SOURCES, MORE, LANG + code (for example LANG FR), FORGET to delete your data. | O ACE dá orientação local verificada. Faça uma pergunta. Comandos: FRAUDE + mensagem para a verificar, DICA + o seu conselho, FONTES, MAIS, LINGUA + código (por exemplo LINGUA EN), ESQUECER para apagar os seus dados. | ACE provides verified local guidance. Ask a question. Commands: FRAUD + message to verify, TIP + your advice, SOURCES, MORE, LANGUAGE + code (e.g., EN LANGUAGE), FORGET to delete your data. |
| 53% |  | `scam.HEADLINES.NO_KNOWN_SIGNS` | I found no known scam signs, but that does not prove it is safe. | Não encontrei sinais de fraude conhecidos, mas isso não prova que seja seguro. | I found no known signs of fraud, but that doesn't prove it's safe. |
| 53% |  | `commands.TEXTS.no_sources` | There is no earlier answer to show sources for. Ask a question first. | Ainda não há resposta para mostrar as fontes. Faça primeiro uma pergunta. | There is still no answer regarding showing the sources. Ask a question first. |
| 53% |  | `services.pregnancy.FIRST` | At {w} weeks, go for your first antenatal check now, before 12 weeks. | Com {w} semanas, faça já a sua primeira consulta pré-natal, antes das 12 semanas. | At {w} weeks, schedule your first prenatal appointment now, before 12 weeks. |
| 54% |  | `services.prices.THIN` | Recent WFP prices for {country} cover too few staple foods to be useful. Ask traders or your agriculture office. | Os preços recentes do PAM para {country} cobrem poucos alimentos básicos para serem úteis. Pergunte aos comerciantes ou aos serviços de agricultura. | Recent WFP prices for {country} cover too few basic foodstuffs to be useful. Ask retailers or agricultural services. |
| 55% |  | `services.pests.REFER` | Ask an extension officer to confirm before you spray. | Peça a um extensionista que confirme antes de pulverizar. | Ask an extension agent to confirm before spraying. |
| 55% |  | `services.pregnancy.NEXT` | At {w} weeks, your next antenatal check is due at {next} weeks. | Com {w} semanas, a sua próxima consulta pré-natal é às {next} semanas. | At {w} weeks, your next prenatal appointment is at {next} weeks. |
| 55% |  | `services.pests.ASK` | Which crop, and what do you see? For example: maize leaves with holes and sawdust. | Que cultura, e o que vê? Por exemplo: folhas de milho com buracos e serradura. | What kind of crop is it, and what do you see? For example: corn husks with holes and sawdust. |
| 56% | yes | `safety.OPENERS.health_urgent` | This sounds urgent. Get medical help now. {numbers} | Isto parece urgente. Procure ajuda médica agora. {numbers} | This seems urgent. Seek medical help now. {numbers} |
| 56% | yes | `safety.OPENERS.self_harm` | I am really sorry you are feeling this way. You deserve support right now. {numbers} | Lamento muito que se sinta assim. Merece apoio agora mesmo. {numbers} | I'm so sorry you feel this way. You deserve support right now. {numbers} |
| 58% |  | `services.warnings.GAP` | {authority} does not publish an official warning feed that ACE can read, so ACE cannot check warnings there. Listen to official bulletins from {authority} on radio and TV. | {authority} não publica avisos num formato que o ACE consiga ler, por isso o ACE não pode verificar avisos aí. Ouça os boletins oficiais na rádio e na televisão. | {authority} does not publish notices in a format that ACE can read, so ACE cannot verify notices there. Listen to official bulletins on radio and television. |
| 60% |  | `services.facility.NONE` | ACE found no public facility within {km} km in its 2019 list. | O ACE não encontrou nenhuma unidade pública a menos de {km} km na sua lista de 2019. | ACE found no public units less than {km} km away in its 2019 list. |
| 62% |  | `commands.TEXTS.help_short` | Ask ACE a question in your language. SCAM + message checks it. FORGET deletes your data. | Faça uma pergunta ao ACE. FRAUDE + mensagem verifica-a. ESQUECER apaga os seus dados. | Ask ACE a question. FRAUD + message verifies it. FORGET deletes your data. |
| 65% | yes | `safety.OPENERS.poisoning` | This sounds like poisoning. Get medical help now and take the container with you. {numbers} | Isto parece um envenenamento. Procure ajuda médica agora e leve a embalagem consigo. {numbers} | This looks like poisoning. Seek medical help now and take the packaging with you. |
| 67% |  | `commands.TEXTS.stopped` | You will not get any further messages from ACE unless you write again. Send FORGET to delete your data. | Não vai receber mais mensagens do ACE, a menos que volte a escrever. Envie ESQUECER para apagar os seus dados. | You will no longer receive messages from ACE unless you write again. Send FORGET to delete your data. |
| 67% |  | `scam.SIGNAL.asks_for_pin` | it asks for your PIN or password | pede o seu PIN ou palavra-passe | It will ask for your PIN or password. |
| 67% |  | `scam.SIGNAL.double_registration` | it claims your SIM is registered twice | diz que o seu cartão SIM está registado duas vezes | It says your SIM card is registered twice. |
| 67% |  | `services.facility.NO_NUMBER` | In an emergency, call your local emergency number. | Em caso de emergência, ligue para o número de emergência local. | In case of emergency, call your local emergency number. |
| 67% |  | `services.pests.NAMES.cassava_mosaic` | cassava mosaic disease | o mosaico da mandioca | cassava mosaic |
| 67% |  | `services.pests.NAMES.fall_armyworm` | fall armyworm | a lagarta do funil do milho | the fall armyworm |
| 67% |  | `services.prices.FAR` | ({km} km from {place}) | (a {km} km de {place}) | (a {km} km from {place}) |
| 67% |  | `services.rain.SPAN` | {a} to {b} | {a} a {b} | {a} a {b} |
| 69% |  | `commands.TEXTS.forgotten` | Done. Everything ACE held about this number has been deleted. | Feito. Tudo o que o ACE guardava sobre este número foi apagado. | Done. Everything that ACE had stored about this number has been deleted. |
| 71% |  | `services.facility.CAVEAT` | From a 2019 list of public facilities; check it is open before you travel. | De uma lista de 2019 de unidades públicas; confirme que está aberta antes de ir. | From a 2019 list of public facilities; confirm that it is open before you go. |
| 71% |  | `scam.REPORT_LINE` | Forward it to 333, it is free. | Reencaminhe-a para o 333, é grátis. | Forward it to 333, it's free. |
| 71% |  | `scam.SIGNAL.confirmation_from_personal_number` | it looks like an M-PESA confirmation but came from a personal number | parece uma confirmação de pagamento mas veio de um número pessoal | It looks like a payment confirmation, but it came from a personal number. |
| 73% | yes | `safety.OPENERS.child_protection` | A child may be in danger. Please get help now. {numbers} | Uma criança pode estar em perigo. Procure ajuda agora. {numbers} | A child may be in danger. Seek help now. {numbers} |
| 73% |  | `services.rain.STALE` | ACE has no current forecast for {place}. Check the {met} forecast. | O ACE não tem previsão atual para {place}. Consulte a previsão do {met}. | ACE currently has no forecast for {place}. Please check the {met} forecast. |
| 73% | yes | `safety.OPENERS.maternal` | This could be a pregnancy emergency. Go to the nearest health facility now. {numbers} | Isto pode ser uma emergência da gravidez. Vá já à unidade de saúde mais próxima. {numbers} | This could be a pregnancy emergency. Go to the nearest health center immediately. |
| 74% |  | `scam.GENERIC_REPORT_LINE` | Do not reply or send money. Report it to your provider using the number on its official website or SIM pack. | Não responda nem envie dinheiro. Denuncie ao seu operador pelo número do site oficial ou da embalagem do cartão SIM. | Do not reply or send money. Report it to your operator using the number on the official website or on the SIM card packaging. |
| 75% |  | `scam.NEUTRAL_ADVICE` | Never share your PIN, and check your mobile money balance before acting on any message. | Nunca partilhe o seu PIN e confirme o saldo da sua carteira móvel antes de agir por causa de uma mensagem. | Never share your PIN and check your mobile wallet balance before acting on a message. |
| 75% |  | `scam.SIGNAL.link` | it contains a link | contém uma ligação | contains a link |
| 75% |  | `services.facility.NEAR` | Nearest public facilities: | Unidades de saúde públicas mais próximas: | Nearest public health facilities: |
| 76% |  | `commands.TEXTS.tip_usage` | Send TIP followed by your advice, for example: TIP neem leaves help against armyworm in Embu. | Envie DICA seguido do seu conselho, por exemplo: DICA as folhas de nim ajudam contra a lagarta do funil. | Send a TIP followed by your advice, for example: TIP: Neem leaves help against fall armyworm. |
| 77% | yes | `safety.OPENERS.gbv` | I am sorry this is happening. You can get help now. {numbers} | Lamento que isto lhe esteja a acontecer. Pode obter ajuda agora. {numbers} | I'm sorry this is happening to you. You can get help now. {numbers} |
| 78% |  | `services.prices.LINE` | {food} at {market}: {currency} {price} {unit} in {month} | {food} no mercado de {market}: {currency} {price} {unit} em {month} | {food} in the {market} market: {currency} {price} {unit} in {month} |
| 79% |  | `commands.TEXTS.no_more` | That is all ACE has on this topic for now. Ask another question or send HELP. | É tudo o que o ACE tem sobre este tema por agora. Faça outra pergunta ou envie AJUDA. | That's all ACE has on this topic for now. Ask another question or send a HELP request. |
| 85% | yes | `safety.FALLBACK_NUMBERS` | Call your local emergency number or go to the nearest health facility. | Ligue para o número de emergência local ou vá à unidade de saúde mais próxima. | Call your local emergency number or go to the nearest health center. |
| 86% |  | `services.pregnancy.ASK` | How many weeks pregnant are you? Reply with a number, for example 22 weeks. | De quantas semanas está grávida? Responda com um número, por exemplo 22 semanas. | How many weeks pregnant are you? Answer with a number, for example 22 weeks. |
| 100% | yes | `safety.EMERGENCY_WORD` | emergency | emergência | emergency |
| 100% | yes | `safety.OR_WORD` | or | ou | or |
| 100% |  | `scam.SIGNAL.dial_code_instruction` | it tells you to dial a code on your phone | manda marcar um código no seu telefone | It tells you to dial a code on your phone. |
| 100% |  | `scam.SIGNS_LABEL` | Warning signs: | Sinais de alerta: | Warning signs: |
| 100% |  | `services.base.DAYS` | Mon | seg | Mon |
| 100% |  | `services.base.DAYS` | Wed | qua | Wed |
| 100% |  | `services.base.DAYS` | Thu | qui | Thu |
| 100% |  | `services.base.DAYS` | Fri | sex | Fri |
| 100% |  | `services.base.DAYS` | Sat | sáb | Sat |
| 100% |  | `services.base.DAYS` | Sun | dom | Sun |
| 100% |  | `services.base.MONTHS` | Jan | jan | Jan |
| 100% |  | `services.base.MONTHS` | Feb | fev | Feb |
| 100% |  | `services.base.MONTHS` | Apr | abr | Apr |
| 100% |  | `services.base.MONTHS` | May | mai | May |
| 100% |  | `services.base.MONTHS` | Nov | nov | Nov |
| 100% |  | `services.facility.EMERGENCY` | Emergency: {numbers}. | Emergência: {numbers}. | Emergency: {numbers}. |
| 100% |  | `services.facility.IN_AREA` | Public hospitals in {place}: | Hospitais públicos em {place}: | Public hospitals in {place}: |
| 100% |  | `services.facility.KM` | {km} km | {km} km | {km} km |
| 100% |  | `services.pests.MAYBE` | Maybe {problem}. | Talvez {problem}. | Maybe {problem}. |
| 100% |  | `services.prices.ITEM` | {food} {currency} {price} {unit} ({month}) | {food} {currency} {price} {unit} ({month}) | {food} {currency} {price} {unit} ({month}) |
| 100% |  | `services.rain.AND` | and | e | and |
| 100% |  | `services.rain.HEAD` | Rain near {place}: | Chuva perto de {place}: | Rain near {place}: |
| 100% |  | `services.rain.HEAVY_LINE` | Heavy rain (20 mm or more) possible {days}. | Chuva forte (20 mm ou mais) possível {days}. | Heavy rain (20 mm or more) possible {days}. |
| 100% |  | `services.rain.WORDS.likely` | likely | provável | likely |
| 100% |  | `services.rain.WORDS.possible` | possible | possível | possible |

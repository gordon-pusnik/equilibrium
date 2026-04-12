package com.example.videopoker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

data class UiCard(val suit: Int, val rank: Int, val held: Boolean, val winning: Boolean = false)
data class GameVariantUi(val id: String, val name: String, val rtpText: String, val isPremium: Boolean = false)

private enum class AppSheet {
    HELP,
    SETTINGS
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AppScreen() }
    }
}

@Composable
private fun AppScreen() {
    var selectedVariantId by remember { mutableStateOf("jacks_or_better_9_6") }
    var bet by remember { mutableIntStateOf(5) }
    var payout by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf("") }
    var suggestedMask by remember { mutableIntStateOf(0) }
    var explanationCategory by remember { mutableStateOf("") }
    var explanationLabel by remember { mutableStateOf("") }
    var explanationSummary by remember { mutableStateOf("") }
    var explanationTip by remember { mutableStateOf("") }
    var showExplanationDetails by remember { mutableStateOf(false) }
    var mistakeSeverity by remember { mutableStateOf("") }
    var mistakeEvDelta by remember { mutableStateOf<Double?>(null) }
    var solverNextBest by remember { mutableStateOf("") }
    var solverBestEv by remember { mutableStateOf<Double?>(null) }
    var solverNextEv by remember { mutableStateOf<Double?>(null) }
    var canDraw by remember { mutableStateOf(false) }
    var autoHoldEnabled by remember { mutableStateOf(true) }
    var autoShowExplanation by remember { mutableStateOf(false) }
    var showPaytable by remember { mutableStateOf(false) }
    var activeSheet by remember { mutableStateOf<AppSheet?>(null) }
    var settingsMessage by remember { mutableStateOf("") }
    val context = LocalContext.current
    val appVersionText = remember(context) {
        try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            packageInfo.versionName ?: "1.0"
        } catch (_: Exception) {
            "1.0"
        }
    }

    val initialCards = remember { mutableStateListOf<UiCard>() }
    val finalCards = remember { mutableStateListOf<UiCard>() }
    val gameVariants = remember {
        listOf(
            GameVariantUi("jacks_or_better_9_6", "Jacks or Better 9/6", "99.54%"),
            GameVariantUi("jacks_or_better_8_5", "Jacks or Better 8/5", "97.30%")
        )
    }
    val selectedVariant = gameVariants.firstOrNull { it.id == selectedVariantId } ?: gameVariants.first()
    var showVariantMenu by remember { mutableStateOf(false) }

    var handle by remember { mutableLongStateOf(0L) }
    DisposableEffect(Unit) {
        handle = NativeBridge.nativeCreate(System.currentTimeMillis())
        onDispose {
            if (handle != 0L) {
                NativeBridge.nativeDestroy(handle)
            }
        }
    }

    LaunchedEffect(autoHoldEnabled, canDraw, bet, selectedVariantId) {
        if (!canDraw || initialCards.size != 5 || handle == 0L) {
            return@LaunchedEffect
        }
        error = ""
        if (!prepareEngine(handle, selectedVariantId)) {
            error = "Failed to set engine"
            return@LaunchedEffect
        }
        val updatedMask = recalculateSuggestedMask(handle, bet, initialCards)
        if (updatedMask < 0) {
            error = "Failed to update suggested holds"
            return@LaunchedEffect
        }
        suggestedMask = updatedMask
        val explanation = explainHold(initialCards, updatedMask)
        explanationCategory = explanation.category
        explanationLabel = explanation.headline
        explanationSummary = explanation.summary
        explanationTip = explanation.patternTip
        val mistakeAnalysis = analyzePlayerHold(handle, initialCards, bet)
        mistakeSeverity = mistakeAnalysis?.severity.orEmpty()
        mistakeEvDelta = mistakeAnalysis?.evDelta
        val solverAnalysis = analyzeSolver(handle, initialCards, bet)
        solverBestEv = solverAnalysis?.bestEv
        solverNextEv = solverAnalysis?.secondEv
        solverNextBest = solverAnalysis?.let { formatHeldCards(initialCards, it.secondMask) }.orEmpty()
        if (autoHoldEnabled) {
            applyHoldMask(initialCards, updatedMask)
        }
    }

    MaterialTheme {
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                verticalArrangement = Arrangement.Top,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { activeSheet = AppSheet.HELP }) {
                        Image(
                            painter = painterResource(id = R.drawable.help),
                            contentDescription = "Help",
                            modifier = Modifier.height(24.dp),
                            contentScale = ContentScale.Fit
                        )
                    }
                    IconButton(onClick = { activeSheet = AppSheet.SETTINGS }) {
                        Image(
                            painter = painterResource(id = R.drawable.settings),
                            contentDescription = "Settings",
                            modifier = Modifier.height(24.dp),
                            contentScale = ContentScale.Fit
                        )
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Box {
                        OutlinedButton(onClick = { showVariantMenu = true }) {
                            Text(selectedVariant.name)
                        }
                        DropdownMenu(
                            expanded = showVariantMenu,
                            onDismissRequest = { showVariantMenu = false }
                        ) {
                            gameVariants.forEach { variant ->
                                DropdownMenuItem(
                                    text = { Text(variant.name) },
                                    onClick = {
                                        selectedVariantId = variant.id
                                        showVariantMenu = false
                                        resetHandState(
                                            initialCards = initialCards,
                                            finalCards = finalCards,
                                            setPayout = { payout = it },
                                            setError = { error = it },
                                            setSuggestedMask = { suggestedMask = it },
                                            setExplanationCategory = { explanationCategory = it },
                                            setExplanationLabel = { explanationLabel = it },
                                            setExplanationSummary = { explanationSummary = it },
                                            setExplanationTip = { explanationTip = it },
                                            setShowExplanationDetails = { showExplanationDetails = it },
                                            setMistakeSeverity = { mistakeSeverity = it },
                                            setMistakeEvDelta = { mistakeEvDelta = it },
                                            setSolverNextBest = { solverNextBest = it },
                                            setSolverBestEv = { solverBestEv = it },
                                            setSolverNextEv = { solverNextEv = it },
                                            setCanDraw = { canDraw = it }
                                        )
                                    }
                                )
                            }
                        }
                    }
                    Text(
                        "Expected RTP (optimal play): ${selectedVariant.rtpText}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.DarkGray,
                        textAlign = TextAlign.Center
                    )
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 24.dp)
                            .background(Color(0xFFF3F3F3), RoundedCornerShape(12.dp))
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        TextButton(
                            onClick = { showPaytable = !showPaytable },
                            modifier = Modifier.align(Alignment.CenterHorizontally)
                        ) {
                            Text(if (showPaytable) "Hide Paytable" else "Show Paytable")
                        }
                        if (showPaytable) {
                            Text(
                                "Paytable ($bet coin${if (bet == 1) "" else "s"})",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center
                            )
                            paytableEntries(selectedVariantId, bet).forEach { entry ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        entry.name,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color.DarkGray
                                    )
                                    Text(
                                        entry.payout.toString(),
                                        style = MaterialTheme.typography.bodySmall,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Button(onClick = { if (bet > 1) bet-- }) { Text("-") }
                    Text("Bet: $bet", fontWeight = FontWeight.Bold)
                    Button(onClick = { if (bet < 5) bet++ }) { Text("+") }

                    Spacer(modifier = Modifier.width(16.dp))

                    Text("Show Best Hold", style = MaterialTheme.typography.bodyMedium)
                    Switch(checked = autoHoldEnabled, onCheckedChange = { autoHoldEnabled = it })
                }

                Spacer(modifier = Modifier.height(4.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = {
                        error = ""
                        if (!prepareEngine(handle, selectedVariantId)) {
                            error = "Failed to set engine"
                            return@Button
                        }
                        val data = NativeBridge.nativeDealSuggested(handle, bet)
                        if (data == null || data.size < 42) {
                            error = "Failed to deal"
                            return@Button
                        }
                        populateFromData(
                            data = data,
                            initialCards = initialCards,
                            finalCards = finalCards,
                            useHeld = autoHoldEnabled,
                            includeFinalCards = false
                        )
                        payout = 0
                        suggestedMask = data[20]
                        val explanation = explainHold(initialCards, suggestedMask)
                        explanationCategory = explanation.category
                        explanationLabel = explanation.headline
                        explanationSummary = explanation.summary
                        explanationTip = explanation.patternTip
                        val mistakeAnalysis = analyzePlayerHold(handle, initialCards, bet)
                        mistakeSeverity = mistakeAnalysis?.severity.orEmpty()
                        mistakeEvDelta = mistakeAnalysis?.evDelta
                        val solverAnalysis = analyzeSolver(handle, initialCards, bet)
                        solverBestEv = solverAnalysis?.bestEv
                        solverNextEv = solverAnalysis?.secondEv
                        solverNextBest = solverAnalysis?.let { formatHeldCards(initialCards, it.secondMask) }.orEmpty()
                        showExplanationDetails = autoShowExplanation
                        canDraw = true
                    }) { Text("Deal") }

                    Button(
                        onClick = {
                            error = ""
                            val holdMask = initialCards.foldIndexed(0) { index, acc, card ->
                                if (card.held) acc or (1 shl index) else acc
                            }
                            val data = NativeBridge.nativeDrawWithMask(handle, bet, holdMask)
                            if (data == null || data.size < 42) {
                                error = "Failed to draw. Deal first."
                                return@Button
                            }
                            populateFromData(
                                data = data,
                                initialCards = initialCards,
                                finalCards = finalCards,
                                useHeld = true,
                                includeFinalCards = true
                            )
                            payout = data[21]
                            explanationCategory = ""
                            explanationLabel = ""
                            explanationSummary = ""
                            explanationTip = ""
                            mistakeSeverity = ""
                            mistakeEvDelta = null
                            solverBestEv = null
                            solverNextEv = null
                            solverNextBest = ""
                            showExplanationDetails = false
                            canDraw = false
                        },
                        enabled = canDraw
                    ) { Text("Draw") }
                }

                if (error.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(error, color = Color.Red, textAlign = TextAlign.Center)
                }

                Spacer(modifier = Modifier.height(6.dp))

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Dealt Hand (tap to hold or discard)", fontWeight = FontWeight.SemiBold)
                    CardRow(
                        cards = initialCards,
                        interactive = canDraw,
                        suggestedMask = if (autoHoldEnabled) suggestedMask else null
                    ) { idx ->
                        if (canDraw) {
                            val card = initialCards[idx]
                            initialCards[idx] = card.copy(held = !card.held)
                            val mistakeAnalysis = analyzePlayerHold(handle, initialCards, bet)
                            mistakeSeverity = mistakeAnalysis?.severity.orEmpty()
                            mistakeEvDelta = mistakeAnalysis?.evDelta
                        }
                    }
                }

                if (explanationLabel.isNotEmpty() && initialCards.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    TextButton(onClick = { showExplanationDetails = !showExplanationDetails }) {
                        Text(if (showExplanationDetails) "Hide Strategy Explanation" else "Strategy Explanation")
                    }
                    if (showExplanationDetails) {
                        Text(
                            "Best Hold: $explanationLabel",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                            textAlign = TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            explanationSummary,
                            style = MaterialTheme.typography.bodySmall,
                            textAlign = TextAlign.Center,
                            color = Color.DarkGray
                        )
                        if (explanationTip.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Pattern tip: $explanationTip",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = Color.DarkGray
                            )
                        }
                        if (mistakeSeverity.isNotEmpty() && mistakeEvDelta != null) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Current choice: ${severityDisplayText(mistakeSeverity)}",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = severityColor(mistakeSeverity)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "EV loss vs solver: ${"%.2f".format(mistakeEvDelta ?: 0.0)}",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = Color.DarkGray
                            )
                        }
                        if (solverBestEv != null && solverNextEv != null && solverNextBest.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Best EV: ${"%.2f".format(solverBestEv)}",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = Color.DarkGray
                            )
                            Text(
                                "Next best: Hold $solverNextBest - EV ${"%.2f".format(solverNextEv)}",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = Color.DarkGray
                            )
                            Text(
                                "EV edge: +${"%.2f".format((solverBestEv ?: 0.0) - (solverNextEv ?: 0.0))}",
                                style = MaterialTheme.typography.bodySmall,
                                textAlign = TextAlign.Center,
                                color = Color.DarkGray
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Final Hand", fontWeight = FontWeight.SemiBold)
                    CardRow(cards = finalCards, interactive = false, suggestedMask = null) {}
                }

                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    "Payout: $payout",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                    color = if (payout > 0) Color(0xFF2E7D32) else Color.Gray
                )
            }

            when (activeSheet) {
                AppSheet.HELP -> TrainerDialog(
                    title = "Help / How to Play",
                    onDismiss = { activeSheet = null }
                ) {
                    HelpScreenContent()
                }
                AppSheet.SETTINGS -> TrainerDialog(
                    title = "Settings / About",
                    onDismiss = { activeSheet = null }
                ) {
                    SettingsScreenContent(
                        autoShowExplanation = autoShowExplanation,
                        onAutoShowExplanationChange = { autoShowExplanation = it },
                        appVersion = appVersionText,
                        onPlaceholderAction = { settingsMessage = it }
                    )
                }
                null -> Unit
            }

            if (settingsMessage.isNotEmpty()) {
                AlertDialog(
                    onDismissRequest = { settingsMessage = "" },
                    confirmButton = {
                        TextButton(onClick = { settingsMessage = "" }) {
                            Text("OK")
                        }
                    },
                    title = { Text("Not Available Yet") },
                    text = { Text(settingsMessage) }
                )
            }
        }
    }
}

@Composable
private fun TrainerDialog(
    title: String,
    onDismiss: () -> Unit,
    content: @Composable () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done")
            }
        },
        title = { Text(title) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(420.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                content()
            }
        }
    )
}

@Composable
private fun HelpScreenContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HelpSection(
            title = "How the trainer works",
            body = "Deal a hand, choose which cards to hold, then draw. The trainer compares your choice to the solver-backed best play."
        )
        HelpSection(
            title = "Holding and discarding",
            body = "Turn off Show Best Hold if you want to choose cards yourself. Tap dealt cards to hold or release them before drawing."
        )
        HelpSection(
            title = "Show Best Hold",
            body = "When this is on, the trainer marks the solver-recommended hold for the current hand."
        )
        HelpSection(
            title = "Mistake levels",
            body = "Perfect means you matched the best play. Very close means the EV loss was tiny. Small, moderate, and major mistakes mean you gave up more value versus the solver."
        )
        HelpSection(
            title = "What EV means",
            body = "EV stands for expected value. It is the average return of a play over many repetitions, not a guarantee for one hand."
        )
        HelpSection(
            title = "Free variants",
            body = "9/6 and 8/5 describe the full house and flush payouts. 9/6 returns more under optimal play than 8/5."
        )
    }
}

@Composable
private fun SettingsScreenContent(
    autoShowExplanation: Boolean,
    onAutoShowExplanationChange: (Boolean) -> Unit,
    appVersion: String,
    onPlaceholderAction: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SettingsToggleRow(
            label = "Auto-show strategy explanation",
            checked = autoShowExplanation,
            onCheckedChange = onAutoShowExplanationChange
        )
        HelpSection(
            title = "Sound and haptics",
            body = "Sound and haptic controls are not supported in the current MVP."
        )
        SettingsActionRow("Restore Purchases") {
            onPlaceholderAction("Purchase restore is reserved for future premium content and is not active in this MVP.")
        }
        SettingsActionRow("Privacy Policy") {
            onPlaceholderAction("A dedicated privacy policy link has not been added to the app yet.")
        }
        SettingsActionRow("Terms") {
            onPlaceholderAction("A dedicated terms link has not been added to the app yet.")
        }
        InfoRow("App Version", appVersion)
    }
}

@Composable
private fun HelpSection(title: String, body: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, fontWeight = FontWeight.SemiBold)
        Text(body, style = MaterialTheme.typography.bodySmall, color = Color.DarkGray)
    }
}

@Composable
private fun SettingsToggleRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun SettingsActionRow(label: String, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFFF3F3F3),
        shape = RoundedCornerShape(10.dp)
    ) {
        TextButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
            Text(label, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Start)
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label)
        Text(value, color = Color.DarkGray)
    }
}

private fun prepareEngine(handle: Long, variantId: String): Boolean {
    if (!NativeBridge.nativeSetEngine(handle, "solver")) {
        return false
    }
    if (!NativeBridge.nativeSetVariant(handle, variantId)) {
        return false
    }
    return true
}

private fun recalculateSuggestedMask(handle: Long, bet: Int, cards: List<UiCard>): Int {
    val suits = IntArray(5) { index -> cards[index].suit }
    val ranks = IntArray(5) { index -> cards[index].rank }
    return NativeBridge.nativeCalculateHoldMask(handle, bet, suits, ranks)
}

private fun applyHoldMask(cards: MutableList<UiCard>, holdMask: Int) {
    for (i in cards.indices) {
        val card = cards[i]
        cards[i] = card.copy(held = (holdMask and (1 shl i)) != 0)
    }
}

private data class HoldExplanationUi(
    val category: String,
    val headline: String,
    val summary: String,
    val patternTip: String
)

private fun explainHold(cards: List<UiCard>, holdMask: Int): HoldExplanationUi {
    val suits = IntArray(5) { index -> cards[index].suit }
    val ranks = IntArray(5) { index -> cards[index].rank }
    val explanation = NativeBridge.nativeExplainHold(suits, ranks, holdMask)
        ?: return HoldExplanationUi("", "", "", "")
    return HoldExplanationUi(
        category = explanation.getOrNull(0).orEmpty(),
        headline = explanation.getOrNull(1).orEmpty(),
        summary = explanation.getOrNull(2).orEmpty(),
        patternTip = explanation.getOrNull(3).orEmpty()
    )
}

private data class PaytableEntry(val name: String, val payout: Int)

private fun paytableEntries(variantId: String, bet: Int): List<PaytableEntry> {
    val fullHouse = if (variantId == "jacks_or_better_8_5") 8 else 9
    val flush = if (variantId == "jacks_or_better_8_5") 5 else 6
    return listOf(
        PaytableEntry("Royal Flush", if (bet == 5) 4000 else bet * 250),
        PaytableEntry("Straight Flush", bet * 50),
        PaytableEntry("Four of a Kind", bet * 25),
        PaytableEntry("Full House", bet * fullHouse),
        PaytableEntry("Flush", bet * flush),
        PaytableEntry("Straight", bet * 4),
        PaytableEntry("Three of a Kind", bet * 3),
        PaytableEntry("Two Pair", bet * 2),
        PaytableEntry("Jacks or Better", bet)
    )
}

private data class SolverAnalysis(val bestMask: Int, val secondMask: Int, val bestEv: Double, val secondEv: Double)
private data class MistakeAnalysisUi(val bestMask: Int, val bestEv: Double, val playerEv: Double, val evDelta: Double, val severity: String)

private fun analyzeSolver(handle: Long, cards: List<UiCard>, bet: Int): SolverAnalysis? {
    val suits = IntArray(5) { index -> cards[index].suit }
    val ranks = IntArray(5) { index -> cards[index].rank }
    val result = NativeBridge.nativeAnalyzeSolver(handle, suits, ranks, bet) ?: return null
    if (result.size < 4) return null
    return SolverAnalysis(
        bestMask = result[0].toInt(),
        secondMask = result[1].toInt(),
        bestEv = result[2],
        secondEv = result[3]
    )
}

private fun analyzePlayerHold(handle: Long, cards: List<UiCard>, bet: Int): MistakeAnalysisUi? {
    val suits = IntArray(5) { index -> cards[index].suit }
    val ranks = IntArray(5) { index -> cards[index].rank }
    val holdMask = cards.foldIndexed(0) { index, acc, card ->
        if (card.held) acc or (1 shl index) else acc
    }
    val result = NativeBridge.nativeAnalyzePlayerHold(handle, suits, ranks, bet, holdMask) ?: return null
    if (result.size < 5) return null
    return MistakeAnalysisUi(
        bestMask = result[0].toIntOrNull() ?: 0,
        bestEv = result[1].toDoubleOrNull() ?: 0.0,
        playerEv = result[2].toDoubleOrNull() ?: 0.0,
        evDelta = result[3].toDoubleOrNull() ?: 0.0,
        severity = result[4]
    )
}

private fun resetHandState(
    initialCards: MutableList<UiCard>,
    finalCards: MutableList<UiCard>,
    setPayout: (Int) -> Unit,
    setError: (String) -> Unit,
    setSuggestedMask: (Int) -> Unit,
    setExplanationCategory: (String) -> Unit,
    setExplanationLabel: (String) -> Unit,
    setExplanationSummary: (String) -> Unit,
    setExplanationTip: (String) -> Unit,
    setShowExplanationDetails: (Boolean) -> Unit,
    setMistakeSeverity: (String) -> Unit,
    setMistakeEvDelta: (Double?) -> Unit,
    setSolverNextBest: (String) -> Unit,
    setSolverBestEv: (Double?) -> Unit,
    setSolverNextEv: (Double?) -> Unit,
    setCanDraw: (Boolean) -> Unit
) {
    initialCards.clear()
    finalCards.clear()
    setPayout(0)
    setError("")
    setSuggestedMask(0)
    setExplanationCategory("")
    setExplanationLabel("")
    setExplanationSummary("")
    setExplanationTip("")
    setShowExplanationDetails(false)
    setMistakeSeverity("")
    setMistakeEvDelta(null)
    setSolverNextBest("")
    setSolverBestEv(null)
    setSolverNextEv(null)
    setCanDraw(false)
}

private fun severityColor(severity: String): Color = when (severity) {
    "perfect" -> Color(0xFF2E7D32)
    "very_close" -> Color(0xFF558B2F)
    "small_leak" -> Color(0xFFF9A825)
    "moderate" -> Color(0xFFEF6C00)
    "major" -> Color(0xFFC62828)
    else -> Color.DarkGray
}

private fun severityDisplayText(severity: String): String = when (severity) {
    "perfect" -> "perfect"
    "very_close" -> "very close"
    "small_leak" -> "small mistake"
    "moderate" -> "moderate mistake"
    "major" -> "major mistake"
    else -> severity
}

private fun formatHeldCards(cards: List<UiCard>, holdMask: Int): String {
    val held = cards.mapIndexedNotNull { index, card ->
        if ((holdMask and (1 shl index)) == 0) null else "${rankText(card.rank)}${suitText(card.suit)}"
    }
    return if (held.isEmpty()) "nothing" else held.joinToString(" ")
}

private fun rankText(rank: Int): String = when (rank) {
    14 -> "A"
    13 -> "K"
    12 -> "Q"
    11 -> "J"
    10 -> "10"
    else -> rank.toString()
}

private fun suitText(suit: Int): String = when (suit) {
    1 -> "s"
    2 -> "c"
    3 -> "h"
    4 -> "d"
    else -> "?"
}

private fun populateFromData(
    data: IntArray,
    initialCards: MutableList<UiCard>,
    finalCards: MutableList<UiCard>,
    useHeld: Boolean,
    includeFinalCards: Boolean
) {
    initialCards.clear()
    finalCards.clear()

    for (i in 0 until 5) {
        val base = i * 4
        val isHeld = if (useHeld) data[base + 2] == 1 else false
        initialCards += UiCard(data[base], data[base + 1], isHeld, data[base + 3] == 1)
    }

    if (includeFinalCards) {
        for (i in 0 until 5) {
            val base = 22 + i * 4
            finalCards += UiCard(data[base], data[base + 1], data[base + 2] == 1, data[base + 3] == 1)
        }
    }
}

@Composable
private fun CardRow(cards: List<UiCard>, interactive: Boolean, suggestedMask: Int?, onTap: (Int) -> Unit) {
    Row(
        horizontalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth()
    ) {
        cards.forEachIndexed { idx, card ->
            val suggested = suggestedMask?.let { (it and (1 shl idx)) != 0 }
            val borderColor = when {
                card.winning -> Color(0xFFFDD835)
                !interactive || suggested == null -> if (card.held) Color(0xFFD17C00) else Color.LightGray
                card.held == suggested && card.held -> Color(0xFF2E7D32)
                card.held == suggested && !card.held -> Color.LightGray
                else -> Color(0xFFC62828)
            }
            val borderWidth = if (card.winning || (interactive && suggested != null && card.held != suggested)) 3.dp else 1.dp
            Box(
                modifier = Modifier
                    .padding(horizontal = 4.dp)
                    .width(64.dp)
                    .height(92.dp)
                    .background(if (card.winning) Color(0xFFFFFDE7) else Color.White, RoundedCornerShape(8.dp))
                    .border(borderWidth, borderColor, RoundedCornerShape(8.dp))
                    .clickable(enabled = interactive) { onTap(idx) },
                contentAlignment = Alignment.Center
            ) {
                Image(
                    painter = cardPainter(card.suit, card.rank),
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize()
                )
                if (card.held && !card.winning) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color.Black.copy(alpha = 0.15f), RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.BottomCenter
                    ) {
                        Text(
                            "HELD",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier
                                .background(Color(0xFFD17C00), RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        )
                    }
                }
                if (card.winning) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color(0xFFFDD835).copy(alpha = 0.1f), RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.BottomCenter
                    ) {
                        Text(
                            "WIN",
                            color = Color.Black,
                            fontWeight = FontWeight.ExtraBold,
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier
                                .background(Color(0xFFFDD835), RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun cardPainter(suit: Int, rank: Int): Painter {
    val context = LocalContext.current
    val name = getCardImageName(suit, rank)
    val id = context.resources.getIdentifier(name, "drawable", context.packageName)
    return if (id != 0) painterResource(id) else painterResource(id = android.R.drawable.ic_menu_report_image)
}

private fun getCardImageName(suit: Int, rank: Int): String {
    val r = when (rank) {
        14 -> "ace"
        13 -> "king"
        12 -> "queen"
        11 -> "jack"
        10 -> "ten"
        9 -> "nine"
        8 -> "eight"
        7 -> "seven"
        6 -> "six"
        5 -> "five"
        4 -> "four"
        3 -> "three"
        2 -> "two"
        else -> ""
    }
    val s = when (suit) {
        1 -> "spades"
        2 -> "clubs"
        3 -> "hearts"
        4 -> "diamonds"
        else -> ""
    }
    return "${r}_${s}"
}

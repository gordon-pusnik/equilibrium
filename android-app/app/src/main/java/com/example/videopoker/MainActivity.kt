package com.example.videopoker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.clickable
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
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
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

data class UiCard(val suit: Int, val rank: Int, val held: Boolean, val winning: Boolean = false)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AppScreen() }
    }
}

@Composable
private fun AppScreen() {
    var engine by remember { mutableStateOf("solver") }
    var bet by remember { mutableIntStateOf(5) }
    var modelPath by remember { mutableStateOf("") }
    var payout by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf("") }
    var suggestedMask by remember { mutableIntStateOf(0) }
    var canDraw by remember { mutableStateOf(false) }
    var autoHoldEnabled by remember { mutableStateOf(true) }

    val initialCards = remember { mutableStateListOf<UiCard>() }
    val finalCards = remember { mutableStateListOf<UiCard>() }

    var handle by remember { mutableLongStateOf(0L) }
    DisposableEffect(Unit) {
        handle = NativeBridge.nativeCreate(System.currentTimeMillis())
        onDispose {
            if (handle != 0L) {
                NativeBridge.nativeDestroy(handle)
            }
        }
    }

    MaterialTheme {
        Column(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                "Video Poker Trainer",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                listOf("solver", "rule", "ml").forEach { mode ->
                    val isSelected = engine == mode
                    if (isSelected) {
                        androidx.compose.material3.Button(
                            onClick = { engine = mode },
                            colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.primary
                            )
                        ) {
                            Text(mode)
                        }
                    } else {
                        androidx.compose.material3.OutlinedButton(
                            onClick = { engine = mode }
                        ) {
                            Text(mode)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { if (bet > 1) bet-- }) { Text("-") }
                Text("Bet: $bet", fontWeight = FontWeight.Bold)
                Button(onClick = { if (bet < 5) bet++ }) { Text("+") }
                
                Spacer(modifier = Modifier.width(16.dp))
                
                Text("Autohold", style = MaterialTheme.typography.bodyMedium)
                Switch(checked = autoHoldEnabled, onCheckedChange = { autoHoldEnabled = it })
            }

            if (engine == "ml") {
                Spacer(modifier = Modifier.height(16.dp))
                OutlinedTextField(
                    value = modelPath,
                    onValueChange = { modelPath = it },
                    label = { Text("ML model path (model.json)") },
                    modifier = Modifier.fillMaxWidth(0.8f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = {
                    error = ""
                    if (!prepareEngine(handle, engine, modelPath)) {
                        error = if (engine == "ml") "Failed to set engine/model" else "Failed to set engine"
                        return@Button
                    }
                    val data = NativeBridge.nativeDealSuggested(handle, bet)
                    if (data == null || data.size < 42) {
                        error = "Failed to deal"
                        return@Button
                    }
                    populateFromData(data, initialCards, finalCards, autoHoldEnabled)
                    payout = 0
                    suggestedMask = data[20]
                    canDraw = true
                }) { Text("Deal Hand") }

                Button(onClick = {
                    error = ""
                    val holdMask = initialCards.foldIndexed(0) { index, acc, card ->
                        if (card.held) acc or (1 shl index) else acc
                    }
                    val data = NativeBridge.nativeDrawWithMask(handle, bet, holdMask)
                    if (data == null || data.size < 42) {
                        error = "Failed to draw. Deal first."
                        return@Button
                    }
                    populateFromData(data, initialCards, finalCards, true)
                    payout = data[21]
                    canDraw = false
                }, enabled = canDraw) { Text("Draw Selected") }
            }

            if (error.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(error, color = Color.Red, textAlign = TextAlign.Center)
            }

            Spacer(modifier = Modifier.height(24.dp))

            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Initial (tap to toggle holds)", fontWeight = FontWeight.SemiBold)
                CardRow(
                    initialCards, 
                    interactive = canDraw, 
                    suggestedMask = if (autoHoldEnabled) suggestedMask else null
                ) { idx ->
                    if (canDraw) {
                        val c = initialCards[idx]
                        initialCards[idx] = c.copy(held = !c.held)
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Final", fontWeight = FontWeight.SemiBold)
                CardRow(finalCards, interactive = false, suggestedMask = null) {}
            }

            Spacer(modifier = Modifier.height(16.dp))
            Text(
                "Payout: $payout",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = if (payout > 0) Color(0xFF2E7D32) else Color.Gray
            )
        }
    }
}

private fun prepareEngine(handle: Long, engine: String, modelPath: String): Boolean {
    if (!NativeBridge.nativeSetEngine(handle, engine)) {
        return false
    }
    if (engine == "ml") {
        if (modelPath.isBlank()) return false
        if (!NativeBridge.nativeSetMlModel(handle, modelPath)) return false
    }
    return true
}

private fun populateFromData(data: IntArray, initialCards: MutableList<UiCard>, finalCards: MutableList<UiCard>, useHeld: Boolean) {
    initialCards.clear()
    finalCards.clear()

    // each card 4 ints: suit, rank, held, winning
    for (i in 0 until 5) {
        val base = i * 4
        val isHeld = if (useHeld) data[base + 2] == 1 else false
        initialCards += UiCard(data[base], data[base + 1], isHeld, data[base + 3] == 1)
    }

    // starts after initial (20 ints) + hold_mask (1) + payout (1) = 22
    for (i in 0 until 5) {
        val base = 22 + i * 4
        finalCards += UiCard(data[base], data[base + 1], data[base + 2] == 1, data[base + 3] == 1)
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
                card.winning -> Color(0xFFFDD835) // Yellow for winning cards
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

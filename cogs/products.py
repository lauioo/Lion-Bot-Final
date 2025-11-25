import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from utils.permissions import require_staff, require_allowed_guild
from utils.embeds import error_embed

DATA_FILE = "data/products.json"
LOCAL_EXAMPLE_IMAGE = "https://dummyimage.com/400x300/000/fff.png&text=No+Image"


def load_products():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_products(products):
    with open(DATA_FILE, "w") as f:
        json.dump(products, f, indent=4)


class ProductCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def forward_attachment_to_storage_channel(self, guild, attachment):
        try:
            from utils.config_loader import get_config
            config = get_config()
            storage_channel_id = config.get("image_storage_channel")

            if not storage_channel_id:
                return None

            channel = guild.get_channel(storage_channel_id)
            if not channel:
                return None

            sent = await channel.send(file=await attachment.to_file())
            return sent.attachments[0].url if sent.attachments else None
        except Exception:
            return None

    def product_embed(self, product):
        embed = discord.Embed(
            title=product["name"],
            description="",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Price", value=f"${product['price']}", inline=False)

        if product.get("stock") is not None:
            embed.add_field(name="Stock", value=str(product["stock"]), inline=False)

        embed.set_image(url=product["image"])
        return embed

    # ---------------------------------------------------------------------
    # /add — NO DESCRIPTION ANYMORE
    # ---------------------------------------------------------------------
    @app_commands.command(name="add", description="Add a new product.")
    @require_allowed_guild()
    @require_staff()
    @app_commands.describe(
        name="Product name",
        price="Product price",
        stock="Product stock",
        image="Attach an image"
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        price: float,
        stock: int,
        image: discord.Attachment
    ):
        await interaction.response.defer(ephemeral=True)

        if image is None:
            return await interaction.followup.send(
                "❌ You must attach an image.", ephemeral=True
            )

        products = load_products()
        new_id = max([p.get("id", 0) for p in products], default=0) + 1

        saved_url = await self.forward_attachment_to_storage_channel(interaction.guild, image)
        image_url = saved_url or image.url or LOCAL_EXAMPLE_IMAGE

        product = {
            "id": new_id,
            "name": name,
            "price": round(float(price), 2),
            "stock": int(stock),
            "image": image_url,
            "message_id": None,
            "channel_id": None,
            "payment_methods": [],
            "discount_percent": 0,
        }

        products.append(product)
        save_products(products)

        embed = self.product_embed(product)

        try:
            sent = await interaction.channel.send(embed=embed)
            product["message_id"] = sent.id
            product["channel_id"] = sent.channel.id
            save_products(products)
        except Exception:
            pass

        await interaction.followup.send(
            f"✅ Product **{name}** (ID {new_id}) added!",
            ephemeral=True,
        )

    # ---------------------------------------------------------------------
    # /editproduct — EDIT PRICE & OPTIONAL STOCK
    # ---------------------------------------------------------------------
    @app_commands.command(name="editproduct", description="Edit price and optionally stock of a product.")
    @require_allowed_guild()
    @require_staff()
    @app_commands.describe(
        product_id="ID of the product",
        price="New price",
        stock="New stock (optional)"
    )
    async def editproduct(
        self,
        interaction: discord.Interaction,
        product_id: int,
        price: float,
        stock: int | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if not product:
            return await interaction.followup.send(
                embed=error_embed("Product not found."), ephemeral=True
            )

        # Apply updates
        product["price"] = round(float(price), 2)
        if stock is not None:
            product["stock"] = int(stock)

        save_products(products)

        # Try updating the embed message if it exists
        if product.get("channel_id") and product.get("message_id"):
            channel = interaction.guild.get_channel(product["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(product["message_id"])
                    await msg.edit(embed=self.product_embed(product))
                except Exception:
                    pass

        await interaction.followup.send(
            f"✏️ Updated **{product['name']}**!\n"
            f"- New price: `${product['price']}`\n"
            (f"- New stock: {product['stock']}" if stock is not None else ""),
            ephemeral=True
        )

    # ---------------------------------------------------------------------
    # /remove
    # ---------------------------------------------------------------------
    @app_commands.command(name="remove", description="Remove a product by ID.")
    @require_allowed_guild()
    @require_staff()
    async def remove(self, interaction: discord.Interaction, product_id: int):
        products = load_products()

        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            return await interaction.response.send_message(
                embed=error_embed("Product not found."), ephemeral=True
            )

        products.remove(product)
        save_products(products)

        await interaction.response.send_message(
            f"🗑️ Removed **{product['name']}**", ephemeral=True
        )

    # ---------------------------------------------------------------------
    # /listproducts
    # ---------------------------------------------------------------------
    @app_commands.command(name="listproducts", description="List all products.")
    @require_allowed_guild()
    async def list_products(self, interaction: discord.Interaction):
        products = load_products()

        if not products:
            return await interaction.response.send_message(
                "⚠️ No products exist.", ephemeral=True
            )

        embeds = []
        for p in products:
            embed = self.product_embed(p)
            embed.set_footer(text=f"Product ID: {p['id']}")
            embeds.append(embed)

        await interaction.response.send_message(
            embeds=embeds, ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ProductCommands(bot))

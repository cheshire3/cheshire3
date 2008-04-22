<?xml version="1.0"?>



<!--
<fis>
	<set support="212" ll="37.5493722562" entropy="0.559482306507" surprise="40063.0962391" gini="0.986121047579">
		<item tid="29116">downing</item>
		<item tid="79536">street</item>
	</set>
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="xml" omit-xml-declaration="yes"/>

	<xsl:template match="/">
		<table id="%%ID%%">	
		<thead><tr><th>#</th><th>support</th><th>terms</th></tr></thead>
		<tbody>		
		  <xsl:for-each select="//set">
		  	<tr>
		  	<td>
					<a>
					<xsl:attribute name="href">
						<xsl:text>javascript: filterLines('</xsl:text>
						    <xsl:for-each select="item">
							<xsl:value-of select="@tid"/>
							<xsl:text> </xsl:text>
						    </xsl:for-each>
						<xsl:text>')</xsl:text>
					</xsl:attribute>
					<xsl:number level="single" count="set" format="1"/>
					</a>
			
			</td>
			<td>
				<xsl:value-of select="@support"/>
			</td>
			<td>
				<xsl:for-each select="item">
					<xsl:value-of select="./text()"/><xsl:text> </xsl:text>
				</xsl:for-each>
			</td>
			</tr>
		   </xsl:for-each>
		   </tbody>
		</table>
	</xsl:template>

</xsl:stylesheet>

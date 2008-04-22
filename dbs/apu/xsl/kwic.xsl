<?xml version="1.0"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<xsl:output method="html" encoding="UTF-8"/>

	<xsl:variable name="offset"><xsl:value-of select="//results/@start"/></xsl:variable>
	<xsl:variable name="totalLines"><xsl:value-of select="//results/@totalLines"/></xsl:variable>
	<xsl:variable name="lines"><xsl:value-of select="count(//line)"/></xsl:variable>
	<xsl:variable name="perPage">20</xsl:variable>
	<xsl:variable name="pages"><xsl:value-of select="round($totalLines div $perPage)"/></xsl:variable>
	<xsl:variable name="currentPage">
		<xsl:choose>
			<xsl:when test="round($offset div $perPage)=0">1</xsl:when>
			<xsl:otherwise><xsl:value-of select="round($offset div $perPage)"/></xsl:otherwise>
		</xsl:choose>
	</xsl:variable>
	<xsl:variable name="rsid"><xsl:value-of select="//results/@rsid"/></xsl:variable>

	<xsl:template match="results">
	
		<div id="kwicResults">


		<div class="header">	
			<div class="resultCount">
				Lines <xsl:value-of select="$offset+1"/> to <xsl:value-of select="$offset+$lines"/> of <xsl:value-of select="$totalLines"/>
			</div>	
		
		
			<div class="navigation">
				<span><a href="javascript:navigate('{$rsid}',0)">First</a></span><span class="divider">|</span>
				<span><a href="javascript:navigate('{$rsid}',{$offset - $perPage})">Previous</a></span>
				<div class="pageNavWidget">Page <input id="pageValue" type="text" value="{$currentPage}" size="3" /> of <xsl:value-of select="$pages"/> <button onclick="navigate('{$rsid}',($('pageValue').value-1)*{$perPage});">Go</button></div>
				<span><a href="javascript:navigate('{$rsid}',{$offset + $perPage})">Next</a></span><span class="divider">|</span>
				<span>Last</span>
			</div>


		</div>
		
			<div id="kwicLines">
				<table id="kwicResults">
					<tbody>
						<xsl:apply-templates select="line"/>
					</tbody>
				</table>
			</div>
		</div>
	</xsl:template>
	
	<xsl:template match="line">
		<tr>
			<xsl:attribute name="class">
				<xsl:choose>
					<xsl:when test="position() mod 2 = 0">even</xsl:when>
					<xsl:otherwise>odd</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<!--  line number (add extra info for links etc?) -->
			<td class="lineNum">
				<a href="javascript:getArticle('{@parent}')">
					<xsl:value-of select="count(preceding-sibling::line)+1+$offset"/>
				</a>
			</td>
			<!--  left context -->
			<td class="left">
				<xsl:apply-templates select="w[following-sibling::node]"/>
			</td>
			<!--  node -->
			<td class="node">
				<xsl:apply-templates select="node"/>
			</td>
			<!--  right context -->
			<td class="right">
				<xsl:apply-templates select="w[preceding-sibling::node]"/>
			</td>
		</tr>
	</xsl:template>
	
	<xsl:template match="node">
		<xsl:apply-templates/>
	</xsl:template>
	
	<xsl:template match="w">
		<!-- <span class="word"> -->
			<xsl:apply-templates/>
			<xsl:text> </xsl:text>
		<!--  </span> -->
	</xsl:template>

</xsl:stylesheet>
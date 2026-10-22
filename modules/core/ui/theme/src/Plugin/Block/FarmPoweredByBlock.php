<?php

declare(strict_types=1);

namespace Drupal\farm_ui_theme\Plugin\Block;

use Drupal\Core\Block\Attribute\Block;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\system\Plugin\Block\SystemPoweredByBlock;

/**
 * Provides a 'Powered by farmOS' block.
 */
#[Block(
  id: 'farm_powered_by_block',
  admin_label: new TranslatableMarkup('Powered by farmOS'),
)]
class FarmPoweredByBlock extends SystemPoweredByBlock {

  /**
   * {@inheritdoc}
   */
  public function build() {
    return ['#markup' => '<span>' . $this->t('Powered by <a href=":poweredby">farmOS</a>', [':poweredby' => 'https://farmOS.org']) . '</span>'];
  }

}
